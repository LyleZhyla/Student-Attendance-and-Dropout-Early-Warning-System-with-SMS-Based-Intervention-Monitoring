from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class RiskAssessment(models.Model):
    class Level(models.TextChoices):
        LOW = 'LOW', 'Low'
        MODERATE = 'MODERATE', 'Moderate'
        HIGH = 'HIGH', 'High'

    class ReviewDecision(models.TextChoices):
        PENDING = 'PENDING', 'Pending review'
        CONFIRMED = 'CONFIRMED', 'Confirmed'
        DISMISSED = 'DISMISSED', 'Dismissed'
        NEEDS_MORE_INFO = 'NEEDS_MORE_INFO', 'Needs more information'

    student = models.ForeignKey('students.Student', on_delete=models.PROTECT, related_name='risk_assessments')
    score = models.PositiveSmallIntegerField(validators=(MinValueValidator(0), MaxValueValidator(100)))
    level = models.CharField(max_length=10, choices=Level.choices, db_index=True)
    indicators = models.JSONField(default=dict, help_text='Explainable score components; never a medical diagnosis.')
    policy_version = models.CharField(max_length=50, default='attendance-v1-draft')
    period_start = models.DateField()
    period_end = models.DateField()
    assessed_on = models.DateField(db_index=True)
    review_decision = models.CharField(
        max_length=20, choices=ReviewDecision.choices, default=ReviewDecision.PENDING, db_index=True
    )
    reviewer_notes = models.TextField(blank=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='generated_risk_assessments',
        null=True, blank=True,
    )
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reviewed_risk_assessments', null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-assessed_on', '-created_at')
        constraints = [models.UniqueConstraint(fields=('student', 'assessed_on'), name='unique_student_risk_assessment_day')]

    def clean(self):
        errors = {}
        if self.score is not None:
            expected_level = self.Level.LOW if self.score < 30 else self.Level.MODERATE if self.score < 60 else self.Level.HIGH
            if self.level and self.level != expected_level:
                errors['level'] = 'Risk level must match the transparent score band.'
        if self.assessed_on and self.assessed_on > timezone.localdate():
            errors['assessed_on'] = 'A risk assessment cannot be generated for a future date.'
        if self.period_start and self.period_end and self.period_end < self.period_start:
            errors['period_end'] = 'Assessment period end must be on or after its start.'
        if self.period_end and self.assessed_on and self.period_end != self.assessed_on:
            errors['period_end'] = 'Assessment period must end on the assessment date.'
        reviewed = self.review_decision != self.ReviewDecision.PENDING
        if reviewed and (not self.reviewed_by_id or not self.reviewed_at):
            errors['reviewed_by'] = 'A completed review requires a reviewer and review timestamp.'
        if not reviewed and (self.reviewed_by_id or self.reviewed_at):
            errors['review_decision'] = 'Pending assessments cannot have completed-review metadata.'
        if self.review_decision in (self.ReviewDecision.DISMISSED, self.ReviewDecision.NEEDS_MORE_INFO) and not self.reviewer_notes.strip():
            errors['reviewer_notes'] = 'Reviewer notes are required for this decision.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.student} — {self.score} ({self.get_level_display()})'


class WellBeingCheckIn(models.Model):
    class SupportPriority(models.TextChoices):
        ROUTINE = 'ROUTINE', 'Routine support'
        PROMPT = 'PROMPT', 'Prompt follow-up'
        URGENT = 'URGENT', 'Urgent human follow-up'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        ACTION_PLANNED = 'ACTION_PLANNED', 'Action planned'
        CLOSED = 'CLOSED', 'Closed'

    student = models.ForeignKey('students.Student', on_delete=models.PROTECT, related_name='well_being_checkins')
    conducted_on = models.DateField(db_index=True)
    questionnaire_version = models.CharField(max_length=50, default='support-check-in-v1-draft')
    privacy_notice_version = models.CharField(max_length=50)
    consent_confirmed = models.BooleanField(default=False)
    responses = models.JSONField(help_text='Restricted support check-in responses; excluded from automated scoring.')
    support_priority = models.CharField(
        max_length=15, choices=SupportPriority.choices, default=SupportPriority.ROUTINE, db_index=True
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN, db_index=True)
    private_notes = models.TextField(blank=True)
    recommended_actions = models.TextField(blank=True)
    conducted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='conducted_well_being_checkins'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reviewed_well_being_checkins',
        null=True, blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-conducted_on', '-created_at')
        constraints = [
            models.UniqueConstraint(
                fields=('student', 'conducted_on'), name='unique_student_well_being_checkin_day'
            )
        ]

    def clean(self):
        errors = {}
        from .well_being import validate_responses

        errors.update(validate_responses(self.responses))
        if self.conducted_on and self.conducted_on > timezone.localdate():
            errors['conducted_on'] = 'A check-in cannot be recorded for a future date.'
        if not self.consent_confirmed:
            errors['consent_confirmed'] = 'Record the student consent or assent before saving responses.'
        if not (self.privacy_notice_version or '').strip():
            errors['privacy_notice_version'] = 'Record the privacy notice version acknowledged by the student.'
        if self.conducted_by_id and (
            not self.conducted_by.is_active
            or (
                self.conducted_by.role not in (self.conducted_by.Role.ADMIN, self.conducted_by.Role.GUIDANCE)
                and not self.conducted_by.is_superuser
            )
        ):
            errors['conducted_by'] = 'Only active Administrators or Guidance Personnel may conduct a check-in.'
        reviewed = self.status != self.Status.OPEN
        if reviewed and (not self.reviewed_by_id or not self.reviewed_at):
            errors['reviewed_by'] = 'Actioned or closed check-ins require reviewer details.'
        if not reviewed and (self.reviewed_by_id or self.reviewed_at):
            errors['status'] = 'Open check-ins cannot have completed-review metadata.'
        if self.status == self.Status.ACTION_PLANNED and not (self.recommended_actions or '').strip():
            errors['recommended_actions'] = 'Record the planned support action.'
        if self.status == self.Status.CLOSED and not (self.private_notes or '').strip():
            errors['private_notes'] = 'Record closure notes before closing the check-in.'
        if self.support_priority == self.SupportPriority.URGENT and not (self.recommended_actions or '').strip():
            errors['recommended_actions'] = 'Urgent human follow-up requires a recorded action plan.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'Well-being check-in: {self.student} on {self.conducted_on}'

# Create your models here.
