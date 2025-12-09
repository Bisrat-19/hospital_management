from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from .models import Treatment
from .serializers import TreatmentSerializer
from patients.models import Patient

class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated
        return getattr(request.user, 'role', None) == 'doctor'

class TreatmentViewSet(viewsets.ModelViewSet):
    queryset = Treatment.objects.select_related('patient', 'doctor', 'appointment').all()
    serializer_class = TreatmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if getattr(user, 'role', None) == 'doctor':
            qs = qs.filter(doctor=user)
        return qs

    def perform_create(self, serializer):
        initial = serializer.validated_data.pop('_resolved_initial_appointment', None)
        if not initial:
            raise ValidationError({"appointment": "Could not resolve initial appointment."})

        if Treatment.objects.filter(appointment=initial).exists():
            raise ValidationError({"appointment": "A treatment already exists for this initial appointment. Update it instead."})

        if initial.doctor_id != self.request.user.id:
            raise ValidationError({"appointment": "You can only create treatments for your own appointments."})

        instance = serializer.save(
            doctor=self.request.user,
            patient=initial.patient,
            appointment=initial
        )

        if instance.follow_up_required is False and initial.status != 'completed':
            initial.status = 'completed'
            initial.save(update_fields=['status'])

        # Update patient status to seen
        Patient.objects.filter(pk=instance.patient_id).update(is_seen=True)

    def perform_update(self, serializer):
        instance = serializer.save()
        if instance.follow_up_required is False and instance.appointment and instance.appointment.status != 'completed':
            instance.appointment.status = 'completed'
            instance.appointment.save(update_fields=['status'])

    @action(detail=False, methods=['get'])
    def today(self, request):
        today = timezone.now().date()
        queryset = self.get_queryset().filter(created_at__date=today)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
