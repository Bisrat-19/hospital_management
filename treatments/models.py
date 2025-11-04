from django.db import models
from django.conf import settings
from patients.models import Patient
from appointments.models import Appointment

class Treatment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='treatments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='treatments')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='treatments')
    
    notes = models.TextField(help_text="Doctor’s notes about the diagnosis and condition")
    prescription = models.TextField(blank=True, null=True, help_text="Prescribed medications or therapy")
    follow_up_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Treatment for {self.patient.full_name} by Dr. {self.doctor.username}"
