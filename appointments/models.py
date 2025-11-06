from django.db import models
from django.db.models import Max, Q
from django.utils import timezone
from django.core.exceptions import ValidationError

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

    # Link follow-ups to their initial appointment
    initial_appointment = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='follow_up_appointments',
        help_text="For follow-up appointments, link to the initial appointment"
    )

    # NEW: treatment linkage (null for initial; required for follow-ups)
    treatment = models.ForeignKey(
        'treatments.Treatment',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='appointments',
        help_text="Follow-ups must reference a Treatment; initial appointments must leave this empty."
    )

    # independent counters
    type_seq = models.PositiveIntegerField(null=True, blank=True, editable=False, db_index=True)
    case_followup_seq = models.PositiveIntegerField(null=True, blank=True, editable=False, db_index=True)

    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-appointment_date']
        constraints = [
            models.UniqueConstraint(
                fields=['appointment_type', 'type_seq'],
                name='unique_type_sequence_per_type'
            ),
            models.CheckConstraint(
                name='treatment_null_for_initial_required_for_followup',
                check=(
                    Q(appointment_type='initial', treatment__isnull=True) |
                    Q(appointment_type='follow_up', treatment__isnull=False)
                )
            ),
        ]

    def __str__(self):
        return f"{self.patient.first_name} - {self.get_appointment_type_display()} ({self.appointment_date.date()})"

    @property
    def display_id(self):
        prefix = 'I' if self.appointment_type == 'initial' else 'F'
        return f"{prefix}-{self.type_seq}" if self.type_seq else prefix

    def clean(self):
        if self.appointment_type == 'initial':
            if self.treatment_id:
                raise ValidationError({'treatment': 'Initial appointments cannot be linked to a Treatment.'})
        elif self.appointment_type == 'follow_up':
            if not self.treatment_id:
                raise ValidationError({'treatment': 'Follow-up appointments must reference an existing Treatment.'})
            if not self.initial_appointment_id:
                raise ValidationError({'initial_appointment': 'Follow-up appointments must link to their initial appointment.'})

        # Ensure treatment belongs to the same patient
        if self.treatment_id and self.patient_id and getattr(self.treatment, 'patient_id', None) != self.patient_id:
            raise ValidationError({'treatment': 'Treatment must belong to the same patient as the appointment.'})

        # Ensure follow-ups reference an initial appointment (not another follow-up)
        if self.initial_appointment_id:
            if self.initial_appointment_id == self.id:
                raise ValidationError({'initial_appointment': 'An appointment cannot reference itself.'})
            if self.appointment_type == 'follow_up' and self.initial_appointment.appointment_type != 'initial':
                raise ValidationError({'initial_appointment': 'Follow-up must reference an initial appointment.'})

    def _assign_type_seq_if_needed(self):
        if self.type_seq is None:
            last = Appointment.objects.filter(
                appointment_type=self.appointment_type
            ).aggregate(m=Max('type_seq'))['m'] or 0
            self.type_seq = last + 1

    def _assign_case_followup_seq_if_needed(self):
        if self.appointment_type == 'follow_up' and self.initial_appointment_id and self.case_followup_seq is None:
            last_case = Appointment.objects.filter(
                appointment_type='follow_up',
                initial_appointment=self.initial_appointment
            ).aggregate(m=Max('case_followup_seq'))['m'] or 0
            self.case_followup_seq = last_case + 1

    def save(self, *args, **kwargs):
        self.full_clean()

        if self._state.adding:
            self._assign_type_seq_if_needed()
            self._assign_case_followup_seq_if_needed()
        else:
            if self.appointment_type == 'follow_up':
                if self.type_seq is None:
                    self._assign_type_seq_if_needed()
                if self.case_followup_seq is None:
                    self._assign_case_followup_seq_if_needed()
        super().save(*args, **kwargs)
