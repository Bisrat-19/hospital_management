import logging
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.core.cache import cache
from django.conf import settings
from .models import Appointment
from .serializers import AppointmentSerializer


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


class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all().order_by('-appointment_date')
    serializer_class = AppointmentSerializer

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsDoctor]  # Doctor creates follow-ups
        elif self.action in ['list']:
            permission_classes = [IsAdminOrReceptionist | IsDoctor]
        elif self.action == 'retrieve':
            permission_classes = [IsAdminOrReceptionist | IsDoctor]
        elif self.action == 'destroy':
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [p() for p in permission_classes]

    def list(self, request, *args, **kwargs):
        cache_key = "appointments_grouped"
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
        
        # Determine if we are filtering by doctor (for doctors) or showing all (for receptionists)
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

    @action(detail=False, methods=['get'], permission_classes=[IsDoctor], url_path='today/Initial')
    def today_initial(self, request):
        today = timezone.now().date()
        doctor = request.user
        qs = Appointment.objects.filter(
            doctor=doctor,
            appointment_date__date=today,
            appointment_type='initial'
        ).order_by('appointment_date')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsDoctor], url_path='today/followup')
    def today_followup(self, request):
        today = timezone.now().date()
        doctor = request.user
        
        qs = Appointment.objects.filter(
            doctor=doctor,
            appointment_date__date=today,
            appointment_type='follow_up'
        ).order_by('appointment_date')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    def _build_grouped_payload(self, qs):
        initial_qs = qs.filter(appointment_type='initial')
        follow_qs = qs.filter(appointment_type='follow_up')
        initial_data = self.get_serializer(initial_qs, many=True).data
        follow_data = self.get_serializer(follow_qs, many=True).data
        return {'initial': initial_data, 'follow_up': follow_data}

    def _invalidate_today_cache(self, instance):
        appt_date = getattr(instance, 'appointment_date', None)
        if appt_date:
            date_str = appt_date.date().isoformat()
            # Invalidate doctor specific cache
            if instance.doctor:
                cache.delete(f"appointments_today_doctor_{instance.doctor.id}_{date_str}")
            # Invalidate all appointments cache (for receptionists)
            cache.delete(f"appointments_today_all_{date_str}")

    def perform_create(self, serializer):
        instance = serializer.save()
        cache.delete("appointments_grouped")
        self._invalidate_today_cache(instance)

    def perform_update(self, serializer):
        instance = serializer.save()
        cache.delete("appointments_grouped")
        self._invalidate_today_cache(instance)

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete("appointments_grouped")
        self._invalidate_today_cache(instance)
