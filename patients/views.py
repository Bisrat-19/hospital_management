import logging
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django.conf import settings
from .models import Patient
from .serializers import PatientSerializer
from .permissions import IsReceptionist, IsAdminOrReceptionist, IsAdminRecDoctor
from core.mixins import CacheResponseMixin, CacheInvalidationMixin

logger = logging.getLogger(__name__)


class PatientViewSet(CacheResponseMixin, CacheInvalidationMixin, viewsets.ModelViewSet):
    queryset = Patient.objects.all().select_related('assigned_doctor').order_by('-created_at')
    serializer_class = PatientSerializer
    cache_key_prefix = "patient"

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update']:
            permission_classes = [IsReceptionist]
        elif self.action == 'list':
            permission_classes = [IsAdminOrReceptionist]
        elif self.action == 'retrieve':
            permission_classes = [IsAdminRecDoctor]
        elif self.action == 'destroy':
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        return [p() for p in permission_classes]

    def get_cache_keys_to_invalidate(self, instance):
        today = timezone.now().date().isoformat()
        keys = [
            "all_patients",
            "all_appointments",
            "all_treatments",
            f"appointments_today_all_{today}",
            f"treatments_today_{today}"
        ]
        
        if instance.pk:
            keys.append(f"patient_{instance.pk}")
            
        if getattr(instance, 'assigned_doctor', None):
            keys.append(f"appointments_today_doctor_{instance.assigned_doctor.id}_{today}")
        
        if self.action == 'destroy':
            self._add_appointment_cache_keys(instance, keys)
        
        return list(set(keys))

    def _add_appointment_cache_keys(self, patient, keys):
        for appt in patient.appointments.all():
            if appt.doctor:
                appt_date = appt.appointment_date.date().isoformat()
                keys.append(f"appointments_today_doctor_{appt.doctor.id}_{appt_date}")

    @action(detail=False, methods=['get'])
    def today(self, request):
        today_date = timezone.now().date()
        queryset = self.get_queryset().filter(created_at__date=today_date)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)