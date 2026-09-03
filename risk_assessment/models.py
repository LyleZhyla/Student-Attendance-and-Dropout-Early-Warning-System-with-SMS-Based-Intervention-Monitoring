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

# Create your models here.
