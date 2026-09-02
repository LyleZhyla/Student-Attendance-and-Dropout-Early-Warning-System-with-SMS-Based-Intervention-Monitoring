from django.db import models


class SMSLog(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'QUEUED', 'Queued'
        SENDING = 'SENDING', 'Sending'
        SENT = 'SENT', 'Sent'
        DELIVERED = 'DELIVERED', 'Delivered'
        FAILED = 'FAILED', 'Failed'

    guardian = models.ForeignKey('students.Guardian', on_delete=models.PROTECT, related_name='sms_logs')
    student = models.ForeignKey('students.Student', on_delete=models.PROTECT, related_name='sms_logs')
    category = models.CharField(max_length=50)
    message = models.TextField()
    recipient_masked = models.CharField(max_length=30)
    event_key = models.CharField(max_length=150, unique=True, help_text='Prevents duplicate messages for one event.')
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.QUEUED)
    provider_reference = models.CharField(max_length=100, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    queued_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

# Create your models here.
