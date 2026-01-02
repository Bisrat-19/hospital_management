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
from .permissions import IsDoctor, IsReceptionist, IsAdminOrReceptionist
from core.mixins import CacheResponseMixin, CacheInvalidationMixin


CACHE_TTL = getattr(settings, 'CACHE_TTL', 300)
logger = logging.getLogger(__name__)

class AppointmentViewSet(CacheResponseMixin, CacheInvalidationMixin, viewsets.ModelViewSet):
    queryset = Appointment.objects.all().select_related('patient', 'doctor').order_by('-appointment_date')
    serializer_class = AppointmentSerializer
    cache_key_prefix = "appointment"

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsDoctor]
        elif self.action in ['list', 'retrieve', 'today']:
            permission_classes = [IsAdminOrReceptionist | IsDoctor]
        elif self.action == 'destroy':
            permission_classes = [IsAdminOrReceptionist]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [p() for p in permission_classes]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'role', None) == 'doctor':
            qs = qs.filter(doctor=user)
        return qs

    def list(self, request, *args, **kwargs):
        user = request.user
        is_doctor = getattr(user, 'role', None) == 'doctor'
        cache_key = f"appointments_list_{'doctor_' + str(user.id) if is_doctor else 'all'}"
        
        cached = cache.get(cache_key)
        if cached:
            logger.debug("appointments.list cache hit for user=%s", user.id)
            return Response(cached)

        logger.debug("appointments.list cache miss for user=%s; rebuilding payload", user.id)
        qs = self.get_queryset()
        payload = self._build_grouped_payload(qs)
        cache.set(cache_key, payload, timeout=CACHE_TTL)
        return Response(payload)

    @action(detail=False, methods=['get'])
    def today(self, request):
        today_date = timezone.now().date()
        user = request.user
        is_doctor = getattr(user, 'role', None) == 'doctor'
        
        cache_key = f"appointments_today_{'doctor_' + str(user.id) if is_doctor else 'all'}_{today_date.isoformat()}"

        cached = cache.get(cache_key)
        if cached:
            logger.debug("appointments.today cache hit for user=%s", user.id)
            return Response(cached)

        logger.debug("appointments.today cache miss for user=%s; rebuilding payload", user.id)
        
        qs = self.get_queryset().filter(appointment_date__date=today_date)
        qs = qs.order_by('appointment_date')
        payload = self._build_grouped_payload(qs)
        cache.set(cache_key, payload, timeout=CACHE_TTL)
        return Response(payload)

    def _build_grouped_payload(self, qs):
        initial_qs = qs.filter(appointment_type='initial')
        follow_qs = qs.filter(appointment_type='follow_up')
        return {
            'initial': self.get_serializer(initial_qs, many=True).data,
            'follow_up': self.get_serializer(follow_qs, many=True).data
        }

    def get_cache_keys_to_invalidate(self, instance):
        keys = ["all_appointments", "appointments_list_all"]
        if instance.doctor:
            keys.append(f"appointments_list_doctor_{instance.doctor.id}")

        appt_date = getattr(instance, 'appointment_date', None)
        if appt_date:
            date_str = appt_date.date().isoformat()
            if instance.doctor:
                keys.append(f"appointments_today_doctor_{instance.doctor.id}_{date_str}")
            keys.append(f"appointments_today_all_{date_str}")
        return keys

    def _check_can_modify(self, appointment):
        if hasattr(self.request.user, 'role') and self.request.user.role == 'receptionist':
            if appointment.patient.is_seen:
                raise PermissionDenied("Cannot modify/cancel appointment - patient has already been seen")

    @action(detail=True, methods=['patch'], permission_classes=[IsReceptionist])
    def cancel(self, request, pk=None):
        appointment = self.get_object()
        self._check_can_modify(appointment)
        
        appointment.status = 'cancelled'
        appointment.save()
        self._invalidate_cache(appointment)
        
        return Response(self.get_serializer(appointment).data)

    def perform_destroy(self, instance):
        self._check_can_modify(instance)
        super().perform_destroy(instance)
