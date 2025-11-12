from rest_framework import serializers
from .models import Patient
from accounts.models import User
from appointments.models import Appointment 
from django.utils import timezone
from django.db import transaction
from payments.serializers import PaymentCreateSerializer

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
    payment_method = serializers.ChoiceField(choices=(('cash', 'cash'), ('chapa', 'chapa')), write_only=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, write_only=True)

    class Meta:
        model = Patient
        fields = [
            'id', 'first_name', 'last_name', 'date_of_birth', 'gender',
            'contact_number', 'address', 'assigned_doctor', 'assigned_doctor_id',
            'queue_number', 'is_seen', 'created_at', 'updated_at',
            'payment_method', 'amount',
        ]
        read_only_fields = ['queue_number']

    def validate(self, attrs):
        if self.instance is None and attrs.get('amount') in (None, ''):
            raise serializers.ValidationError({'amount': 'This field is required.'})

        first_name = attrs.get('first_name') or (self.instance.first_name if self.instance else None)
        last_name = attrs.get('last_name') or (self.instance.last_name if self.instance else None)
        phone = attrs.get('contact_number') or (self.instance.contact_number if self.instance else None)

        if first_name and last_name and phone:
            qs = Patient.objects.filter(
                first_name__iexact=first_name.strip(),
                last_name__iexact=last_name.strip(),
                contact_number=phone
            )
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Patient already exists.")
        return attrs

    def create(self, validated_data):
        payment_method = validated_data.pop('payment_method')
        amount = validated_data.pop('amount', None)

        if 'assigned_doctor' not in validated_data or validated_data['assigned_doctor'] is None:
            doctor = User.objects.filter(role='doctor').first()
            validated_data['assigned_doctor'] = doctor


        with transaction.atomic():
            patient = super().create(validated_data)

            Appointment.objects.create(
                patient=patient,
                doctor=patient.assigned_doctor,
                appointment_date=timezone.now(),
                appointment_type='initial',
                notes='Initial consultation upon registration.'
            )

            pay_input = {
                "patient_id": patient.id,
                "amount": str(amount),
                "payment_method": payment_method,
            }
            pay_serializer = PaymentCreateSerializer(data=pay_input, context=self.context)
            pay_serializer.is_valid(raise_exception=True)
            payment = pay_serializer.save()

        # Use centralized payment response from payments app
        self._payment_info = pay_serializer.build_response(payment)
        return patient

    def update(self, instance, validated_data):
        assigned_doctor = validated_data.pop('assigned_doctor', None)
        if assigned_doctor:
            instance.assigned_doctor = assigned_doctor

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        if hasattr(self, "_payment_info"):
            rep["payment"] = self._payment_info
        return rep
