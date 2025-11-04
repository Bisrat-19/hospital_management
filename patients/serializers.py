from rest_framework import serializers
from .models import Patient
from accounts.models import User
from appointments.models import Appointment 
from django.utils import timezone

class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class PatientSerializer(serializers.ModelSerializer):
    assigned_doctor = DoctorSerializer(read_only=True)
    assigned_doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='doctor'),
        source='assigned_doctor',
        write_only=True,
        required=False
    )

    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'date_of_birth', 'gender',
            'contact_number', 'address', 'assigned_doctor', 'assigned_doctor_id',
            'queue_number', 'is_seen', 'created_at', 'updated_at'
        ]
        read_only_fields = ['queue_number']

    def create(self, validated_data):
        # ✅ Auto-assign doctor if not provided
        if 'assigned_doctor' not in validated_data or validated_data['assigned_doctor'] is None:
            doctor = User.objects.filter(role='doctor').first()
            validated_data['assigned_doctor'] = doctor

        # ✅ Prevent duplicate patient
        dob = validated_data.get('date_of_birth')
        if Patient.objects.filter(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            date_of_birth=dob
        ).exists():
            raise serializers.ValidationError("Patient with same name and DOB already exists.")

        # ✅ Create patient
        patient = super().create(validated_data)

        # ✅ Automatically create an initial appointment
        Appointment.objects.create(
            patient=patient,
            doctor=patient.assigned_doctor,
            appointment_date=timezone.now(),
            appointment_type='initial',
            notes='Initial consultation upon registration.'
        )

        return patient

    def update(self, instance, validated_data):
        # Handle assigned doctor separately
        assigned_doctor = validated_data.pop('assigned_doctor', None)
        if assigned_doctor:
            instance.assigned_doctor = assigned_doctor

        # Update other fields normally
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
