from rest_framework import serializers
from .models import Treatment
from patients.serializers import PatientSerializer, DoctorSerializer

class TreatmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.username', read_only=True)

    class Meta:
        model = Treatment
        fields = [
            'id',
            'patient',        
            'patient_name',
            'doctor',         
            'doctor_name',
            'appointment',    
            'notes',
            'prescription',
            'follow_up_required',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'doctor_name', 'patient_name', 'patient', 'doctor']

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['patient'] = PatientSerializer(instance.patient).data
        response['doctor'] = DoctorSerializer(instance.doctor).data
        return response

    def validate(self, attrs):
        request = self.context.get('request')
        appt = attrs.get('appointment') or getattr(self.instance, 'appointment', None)
        
        if not appt:
            raise serializers.ValidationError({"appointment": "Appointment is required."})

        initial = self._resolve_initial_appointment(appt)
        self._validate_treatment_exists(initial)
        self._validate_doctor_permission(request, initial)

        attrs['_resolved_initial_appointment'] = initial
        return attrs

    def _resolve_initial_appointment(self, appt):
        initial = appt if appt.appointment_type == 'initial' else appt.initial_appointment
        if not initial:
            raise serializers.ValidationError({"appointment": "Follow-up appointment must reference an initial appointment."})
        return initial

    def _validate_treatment_exists(self, initial):
        if not self.instance and Treatment.objects.filter(appointment=initial).exists():
            raise serializers.ValidationError({"appointment": "A treatment already exists for this initial appointment."})

    def _validate_doctor_permission(self, request, initial):
        if request and getattr(request.user, 'role', None) == 'doctor':
            if initial.doctor_id != request.user.id:
                raise serializers.ValidationError({"appointment": "You can only manage treatments for your own appointments."})
