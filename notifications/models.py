from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class SMSLog(models.Model):
    class Category(models.TextChoices):
        GENERAL = 'GENERAL', 'General notice'
        ATTENDANCE = 'ATTENDANCE', 'Attendance notice'
        MEETING = 'MEETING', 'Meeting notice'
        HOME_VISIT = 'HOME_VISIT', 'Home visit notice'

    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        SENDING = 'SENDING', 'Sending'
        SENT = 'SENT', 'Sent'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'
        CANCELLED = 'CANCELLED', 'Cancelled'

    guardian = models.ForeignKey('students.Guardian', on_delete=models.PROTECT, related_name='sms_logs')
    student = models.ForeignKey('students.Student', on_delete=models.PROTECT, related_name='sms_logs')
    category = models.CharField(max_length=50, choices=Category.choices)
    message = models.TextField()
    recipient_masked = models.CharField(max_length=30)
    event_key = models.CharField(max_length=150, unique=True, help_text='Prevents duplicate messages for one event.')
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.QUEUED)
    provider_reference = models.CharField(max_length=100, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_sms_logs'
    )
    queued_at = models.DateTimeField(auto_now_add=True)
    last_attempted_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-queued_at',)

    def clean(self):
        errors = {}
        if self.guardian_id and self.student_id:
            if not self.guardian.students.filter(pk=self.student_id).exists():
                errors['guardian'] = 'The guardian is not linked to this student.'
            if not self.guardian.sms_consent:
                errors['guardian'] = 'The guardian has not consented to SMS notifications.'
            if not self.guardian.mobile_verified:
                errors['guardian'] = 'The guardian mobile number has not been verified.'
        if self.category and self.category not in self.Category.values:
            errors['category'] = 'Choose a supported notification category.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.get_category_display()} for {self.student} to {self.guardian}'

# Create your models here.
