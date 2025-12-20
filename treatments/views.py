from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from .models import Treatment
from .serializers import TreatmentSerializer
from .permissions import IsDoctor
from patients.models import Patient
from core.mixins import CacheResponseMixin, CacheInvalidationMixin

class TreatmentViewSet(CacheResponseMixin, CacheInvalidationMixin, viewsets.ModelViewSet):
    queryset = Treatment.objects.select_related('patient', 'doctor', 'appointment').all()
    serializer_class = TreatmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]
    cache_key_prefix = "treatment"

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'role', None) == 'doctor':
            from django.utils import timezone
            today = timezone.now().date()
            qs = qs.filter(doctor=user, created_at__date=today)
        return qs

    def get_cache_keys_to_invalidate(self, instance):
        keys = ["all_treatments", "all_appointments"]
        today = timezone.now().date().isoformat()
        keys.append(f"treatments_today_{today}")
        
        if instance.appointment:
            self._add_appointment_cache_keys(instance.appointment, keys)
        return keys

    def _add_appointment_cache_keys(self, appt, keys):
        if appt.appointment_date:
            date_str = appt.appointment_date.date().isoformat()
            if appt.doctor_id:
                keys.append(f"appointments_today_doctor_{appt.doctor_id}_{date_str}")
            keys.append(f"appointments_today_all_{date_str}")

    def perform_create(self, serializer):
        initial = serializer.validated_data.pop('_resolved_initial_appointment', None)
        if not initial:
            raise ValidationError({"appointment": "Could not resolve initial appointment."})

        instance = serializer.save(
            doctor=self.request.user,
            patient=initial.patient,
            appointment=initial
        )

        self._update_related_models(instance, initial)
        self._invalidate_cache(instance)

    def _update_related_models(self, instance, appointment):
        if instance.follow_up_required is False and appointment.status != 'completed':
            appointment.status = 'completed'
            appointment.save(update_fields=['status'])

        Patient.objects.filter(pk=instance.patient_id).update(is_seen=True)

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.follow_up_required is False and instance.appointment and instance.appointment.status != 'completed':
            instance.appointment.status = 'completed'
            instance.appointment.save(update_fields=['status'])
            
        self._invalidate_cache(instance)
        
    @action(detail=False, methods=['get'])
    def today(self, request):
        today_date = timezone.now().date()
        queryset = self.get_queryset().filter(created_at__date=today_date)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
