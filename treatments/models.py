from django.db import models
from django.conf import settings
from patients.models import Patient
from appointments.models import Appointment

class Treatment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='treatments')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='treatments')

    # Use FK (not OneToOne) to avoid UNIQUE errors; enforce uniqueness in code
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name='treatments',
        null=True,
        blank=True,
        help_text="Always points to the initial appointment for this case"
    )

    notes = models.TextField(help_text="Doctor’s notes about the diagnosis and condition")
    prescription = models.TextField(blank=True, null=True, help_text="Prescribed medications or therapy")
    follow_up_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['patient'], name='unique_treatment_per_patient')
        ]

    def __str__(self):
        name = getattr(self.patient, 'full_name', f'{self.patient.first_name} {self.patient.last_name}')
        return f"Treatment for {name} by Dr. {self.doctor.username}"
