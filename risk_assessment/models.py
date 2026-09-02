from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class RiskAssessment(models.Model):
    class Level(models.TextChoices):
        LOW = 'LOW', 'Low'
        MODERATE = 'MODERATE', 'Moderate'
        HIGH = 'HIGH', 'High'

    student = models.ForeignKey('students.Student', on_delete=models.PROTECT, related_name='risk_assessments')
    score = models.PositiveSmallIntegerField(validators=(MinValueValidator(0), MaxValueValidator(100)))
    level = models.CharField(max_length=10, choices=Level.choices, db_index=True)
    indicators = models.JSONField(default=dict, help_text='Explainable score components; never a medical diagnosis.')
    assessed_on = models.DateField(db_index=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reviewed_risk_assessments', null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=('student', 'assessed_on'), name='unique_student_risk_assessment_day')]

# Create your models here.
