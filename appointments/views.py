import logging
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from .models import Appointment
from .serializers import AppointmentSerializer


from core.mixins import CacheResponseMixin, CacheInvalidationMixin


CACHE_TTL = getattr(settings, 'CACHE_TTL', 300)
logger = logging.getLogger(__name__)

class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'doctor'


class IsReceptionist(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'receptionist'


class IsAdminOrReceptionist(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) in ['admin', 'receptionist']


class AppointmentViewSet(CacheResponseMixin, CacheInvalidationMixin, viewsets.ModelViewSet):
    queryset = Appointment.objects.all().order_by('-appointment_date')
    serializer_class = AppointmentSerializer
    cache_key_prefix = "appointment"

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsDoctor]  
        elif self.action in ['list']:
            permission_classes = [IsAdminOrReceptionist | IsDoctor]
        elif self.action == 'retrieve':
            permission_classes = [IsAdminOrReceptionist | IsDoctor]
        elif self.action == 'destroy':
            permission_classes = [IsAdminOrReceptionist]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [p() for p in permission_classes]

    def list(self, request, *args, **kwargs):
        cache_key = "all_appointments" 
        cached = cache.get(cache_key)
        if cached:
            logger.debug("appointments.list cache hit")
            return Response(cached)

        logger.debug("appointments.list cache miss; rebuilding payload")
        qs = self.get_queryset().order_by('-appointment_date')
        payload = self._build_grouped_payload(qs)
        cache.set(cache_key, payload, timeout=CACHE_TTL)
        return Response(payload)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminOrReceptionist | IsDoctor])
    def today(self, request):
        today = timezone.now().date()
        user = request.user
        is_doctor = getattr(user, 'role', None) == 'doctor'
        
        if is_doctor:
            cache_key = f"appointments_today_doctor_{user.id}_{today.isoformat()}"
        else:
            cache_key = f"appointments_today_all_{today.isoformat()}"

        cached = cache.get(cache_key)
        if cached:
            logger.debug("appointments.today cache hit for user=%s", user.id)
            return Response(cached)

        logger.debug("appointments.today cache miss for user=%s; rebuilding payload", user.id)
        
        qs = Appointment.objects.filter(appointment_date__date=today)
        if is_doctor:
            qs = qs.filter(doctor=user)
            
        qs = qs.order_by('appointment_date')
        payload = self._build_grouped_payload(qs)
        cache.set(cache_key, payload, timeout=CACHE_TTL)
        return Response(payload)

    def _build_grouped_payload(self, qs):
        initial_qs = qs.filter(appointment_type='initial')
        follow_qs = qs.filter(appointment_type='follow_up')
        initial_data = self.get_serializer(initial_qs, many=True).data
        follow_data = self.get_serializer(follow_qs, many=True).data
        return {'initial': initial_data, 'follow_up': follow_data}

    def get_cache_keys_to_invalidate(self, instance):
        keys = ["all_appointments"]
        appt_date = getattr(instance, 'appointment_date', None)
        if appt_date:
            date_str = appt_date.date().isoformat()
            if instance.doctor:
                keys.append(f"appointments_today_doctor_{instance.doctor.id}_{date_str}")
            keys.append(f"appointments_today_all_{date_str}")
        return keys

    @action(detail=True, methods=['patch'], permission_classes=[IsReceptionist])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        
        if appointment.patient.is_seen:
            return Response(
                {"error": "Cannot cancel appointment - patient has already been seen"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        appointment.status = 'cancelled'
        appointment.save()
        
        self._invalidate_cache(appointment)
        
        return Response(AppointmentSerializer(appointment).data)

    def perform_destroy(self, instance):
        if hasattr(self.request.user, 'role') and self.request.user.role == 'receptionist':
            if instance.patient.is_seen:
                raise PermissionDenied("Cannot delete appointment - patient has already been seen")
        
        super().perform_destroy(instance)
