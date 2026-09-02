from django.conf import settings
from django.db import models


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
    scheduled_for = models.DateTimeField(null=True, blank=True)
    findings = models.TextField(blank=True)
    follow_up_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

# Create your models here.
