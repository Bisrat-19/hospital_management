from django.db import models
from django.utils import timezone
from patients.models import Patient
from django.db.models import Q  # added

class Payment(models.Model):
    METHOD_CHOICES = [
        ('cash', 'Cash'),
        ('chapa', 'Chapa'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    reference = models.CharField(max_length=100, unique=True, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.first_name} - {self.amount} ({self.status})"

    class Meta:
        # Ensure only one successful (paid) payment exists per patient
        constraints = [
            models.UniqueConstraint(
                fields=['patient'],
                condition=Q(status='paid'),
                name='uniq_paid_payment_per_patient',
            ),
        ]
