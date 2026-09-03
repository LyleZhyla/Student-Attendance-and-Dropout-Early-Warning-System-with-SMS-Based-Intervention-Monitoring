from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class InterventionCase(models.Model):
    class Status(models.TextChoices):
        FOR_REVIEW = 'FOR_REVIEW', 'For Review'
        CONTACTING_PARENT = 'CONTACTING_PARENT', 'Contacting Parent'
        MEETING_SCHEDULED = 'MEETING_SCHEDULED', 'Meeting Scheduled'
        HOME_VISIT_SCHEDULED = 'HOME_VISIT_SCHEDULED', 'Home Visit Scheduled'
        UNDER_INTERVENTION = 'UNDER_INTERVENTION', 'Under Intervention'
        FOR_FOLLOW_UP = 'FOR_FOLLOW_UP', 'For Follow-up'
        RESOLVED = 'RESOLVED', 'Resolved'
        CLOSED = 'CLOSED', 'Closed'

    student = models.ForeignKey('students.Student', on_delete=models.PROTECT, related_name='intervention_cases')
    reason = models.TextField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.FOR_REVIEW, db_index=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='assigned_interventions')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='created_interventions'
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    findings = models.TextField(blank=True)
    follow_up_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-updated_at',)

    def clean(self):
        errors = {}
        if self.assigned_to_id:
            allowed_roles = (
                self.assigned_to.Role.ADMIN, self.assigned_to.Role.TEACHER, self.assigned_to.Role.GUIDANCE
            )
            if not self.assigned_to.is_active or (
                self.assigned_to.role not in allowed_roles and not self.assigned_to.is_superuser
            ):
                errors['assigned_to'] = 'Assign the case to active intervention personnel.'
        scheduled_statuses = (self.Status.MEETING_SCHEDULED, self.Status.HOME_VISIT_SCHEDULED)
        if self.status in scheduled_statuses and not self.scheduled_for:
            errors['scheduled_for'] = 'A date and time are required for a scheduled meeting or home visit.'
        if self.scheduled_for and self.status in scheduled_statuses and self.scheduled_for <= timezone.now():
            errors['scheduled_for'] = 'The meeting or home visit must be scheduled in the future.'
        if self.status == self.Status.FOR_FOLLOW_UP and not self.follow_up_on:
            errors['follow_up_on'] = 'A follow-up date is required.'
        if self.follow_up_on and self.status == self.Status.FOR_FOLLOW_UP and self.follow_up_on < timezone.localdate():
            errors['follow_up_on'] = 'The follow-up date cannot be in the past.'
        if self.status in (self.Status.RESOLVED, self.Status.CLOSED) and not self.findings.strip():
            errors['findings'] = 'Findings are required before resolving or closing a case.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'Case {self.pk or "new"}: {self.student}'


class InterventionActivity(models.Model):
    class Type(models.TextChoices):
        NOTE = 'NOTE', 'Case note'
        PARENT_CONTACT = 'PARENT_CONTACT', 'Parent contact attempt'
        MEETING = 'MEETING', 'Meeting'
        HOME_VISIT = 'HOME_VISIT', 'Home visit'
        FOLLOW_UP = 'FOLLOW_UP', 'Follow-up'
        STATUS_CHANGE = 'STATUS_CHANGE', 'Status change'

    class Channel(models.TextChoices):
        PHONE = 'PHONE', 'Phone call'
        SMS = 'SMS', 'SMS'
        IN_PERSON = 'IN_PERSON', 'In person'
        OTHER = 'OTHER', 'Other'

    class Outcome(models.TextChoices):
        REACHED = 'REACHED', 'Reached guardian'
        NO_ANSWER = 'NO_ANSWER', 'No answer'
        INVALID_CONTACT = 'INVALID_CONTACT', 'Invalid contact details'
        RESCHEDULED = 'RESCHEDULED', 'Rescheduled'
        COMPLETED = 'COMPLETED', 'Completed'
        REFERRED = 'REFERRED', 'Referred for further support'

    case = models.ForeignKey(InterventionCase, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=30, choices=Type.choices)
    guardian = models.ForeignKey(
        'students.Guardian', on_delete=models.PROTECT, null=True, blank=True, related_name='intervention_activities'
    )
    channel = models.CharField(max_length=20, choices=Channel.choices, blank=True)
    outcome = models.CharField(max_length=30, choices=Outcome.choices, blank=True)
    notes = models.TextField()
    occurred_at = models.DateTimeField(default=timezone.now)
    next_action_on = models.DateField(null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='recorded_intervention_activities'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-occurred_at', '-created_at')

    def clean(self):
        errors = {}
        if not self.notes.strip():
            errors['notes'] = 'Activity notes are required.'
        if self.activity_type == self.Type.PARENT_CONTACT:
            if not self.guardian_id:
                errors['guardian'] = 'Choose the guardian contacted.'
            if not self.channel:
                errors['channel'] = 'Choose the contact channel.'
            if not self.outcome:
                errors['outcome'] = 'Record the contact outcome.'
        if self.guardian_id and self.case_id and not self.guardian.students.filter(pk=self.case.student_id).exists():
            errors['guardian'] = 'The guardian is not linked to this case student.'
        if self.occurred_at and self.occurred_at > timezone.now():
            errors['occurred_at'] = 'An activity cannot occur in the future.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.get_activity_type_display()} for {self.case}'

# Create your models here.
