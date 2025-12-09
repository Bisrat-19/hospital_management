from django.db import models
from django.conf import settings
from django.utils import timezone

class Patient(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    contact_number = models.CharField(max_length=20)
    address = models.TextField(blank=True)

    assigned_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'doctor'}
    )

    queue_number = models.PositiveIntegerField(null=True, blank=True)
    is_seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-assign queue number per day
        if not self.queue_number:
            today = timezone.now().date()
            today_patients = Patient.objects.filter(created_at__date=today)
            last_number = today_patients.aggregate(models.Max('queue_number'))['queue_number__max'] or 0
            self.queue_number = last_number + 1
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} (Queue {self.queue_number})"
