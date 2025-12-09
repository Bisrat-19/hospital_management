from rest_framework import serializers
from .models import Appointment
from accounts.models import User
from patients.models import Patient
from treatments.models import Treatment


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ['id', 'first_name', 'last_name','gender', 'date_of_birth']


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

    treatment = serializers.PrimaryKeyRelatedField(
        queryset=Treatment.objects.all(),
        required=False,
        allow_null=True
    )

    initial_appointment = serializers.PrimaryKeyRelatedField(read_only=True)
    initial_appointment_id = serializers.PrimaryKeyRelatedField(
        queryset=Appointment.objects.all(),
        source='initial_appointment',
        write_only=True,
        required=False,
        allow_null=True
    )

    display_id = serializers.CharField(read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id',
            'display_id',
            'patient', 'patient_id',
            'doctor', 'doctor_id',
            'appointment_date',
            'appointment_type',
            'initial_appointment', 'initial_appointment_id',
            'treatment',              
            'notes',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ('type_seq', 'case_followup_seq', 'created_at', 'updated_at')

    def validate(self, attrs):
        appt_type = attrs.get('appointment_type') or getattr(self.instance, 'appointment_type', 'initial')
        initial_appt = attrs.get('initial_appointment')
        patient = attrs.get('patient') or getattr(self.instance, 'patient', None)
        doctor = attrs.get('doctor') or getattr(self.instance, 'doctor', None)
        treatment = attrs.get('treatment', getattr(self.instance, 'treatment', None))

        if appt_type == 'follow_up':
            if not initial_appt:
                raise serializers.ValidationError({"initial_appointment_id": "Follow-up appointments must reference an initial appointment."})
            if initial_appt.appointment_type != 'initial':
                raise serializers.ValidationError({"initial_appointment_id": "Must point to an initial appointment."})
            if patient and patient != initial_appt.patient:
                raise serializers.ValidationError({"patient_id": "Follow-up patient must match the initial appointment's patient."})
            if doctor and doctor != initial_appt.doctor:
                raise serializers.ValidationError({"doctor_id": "Follow-up doctor must match the initial appointment's doctor."})
            if treatment is None:
                raise serializers.ValidationError({'treatment': 'Follow-up requires a treatment ID.'})
            if treatment.patient_id != getattr(patient, 'id', None):
                raise serializers.ValidationError({'treatment': 'Treatment must belong to the same patient.'})
    
            attrs['patient'] = initial_appt.patient
            attrs['doctor'] = initial_appt.doctor
        else:
            if initial_appt is not None:
                raise serializers.ValidationError({"initial_appointment_id": "Initial appointments cannot set initial_appointment."})
        return attrs

    def create(self, validated_data):
        if validated_data.get('appointment_type') == 'follow_up':
            validated_data['status'] = 'pending'
        return super().create(validated_data)
