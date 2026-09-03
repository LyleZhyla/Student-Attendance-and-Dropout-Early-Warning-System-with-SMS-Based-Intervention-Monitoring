from django.contrib import admin

from .models import RiskAssessment

@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'score', 'level', 'review_decision', 'assessed_on', 'reviewed_by')
    list_filter = ('level', 'review_decision', 'assessed_on', 'policy_version')
    search_fields = ('student__first_name', 'student__last_name', 'student__learner_reference_number')
    readonly_fields = (
        'student', 'score', 'level', 'indicators', 'policy_version', 'period_start', 'period_end',
        'assessed_on', 'generated_by', 'created_at', 'updated_at',
    )

# Register your models here.
