from django.db import models
from django.utils import timezone
from accounts.models import User
from patients.models import Patient


class Appointment(models.Model):
    APPOINTMENT_TYPES = [
        ('initial', 'Initial Consultation'),
        ('follow_up', 'Follow-up Consultation'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='appointments'
    )
    doctor = models.ForeignKey(
        User, on_delete=models.CASCADE, limit_choices_to={'role': 'doctor'}, related_name='doctor_appointments'
    )
    appointment_date = models.DateTimeField(default=timezone.now)
    appointment_type = models.CharField(max_length=20, choices=APPOINTMENT_TYPES, default='initial')
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date']

    def __str__(self):
        return f"{self.patient.first_name} - {self.get_appointment_type_display()} ({self.appointment_date.date()})"
