from rest_framework import serializers
from .models import Appointment
from accounts.models import User
from patients.models import Patient


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'first_name', 'last_name']


class AppointmentSerializer(serializers.ModelSerializer):
    patient = PatientSerializer(read_only=True)
    patient_id = serializers.PrimaryKeyRelatedField(
        queryset=Patient.objects.all(), source='patient', write_only=True
    )

    doctor = DoctorSerializer(read_only=True)
    doctor_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role='doctor'),
        source='doctor',
        write_only=True
    )

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_id', 'doctor', 'doctor_id',
            'appointment_date', 'appointment_type', 'notes',
            'status', 'created_at', 'updated_at'
        ]

    def create(self, validated_data):
        # Automatically mark follow-up appointments as 'pending'
        if validated_data.get('appointment_type') == 'follow_up':
            validated_data['status'] = 'pending'
        return super().create(validated_data)
