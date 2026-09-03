from django.contrib import admin

from .models import RiskAssessment, WellBeingCheckIn

@admin.register(RiskAssessment)
class RiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'score', 'level', 'review_decision', 'assessed_on', 'reviewed_by')
    list_filter = ('level', 'review_decision', 'assessed_on', 'policy_version')
    search_fields = ('student__first_name', 'student__last_name', 'student__learner_reference_number')
    readonly_fields = (
        'student', 'score', 'level', 'indicators', 'policy_version', 'period_start', 'period_end',
        'assessed_on', 'generated_by', 'created_at', 'updated_at',
    )


@admin.register(WellBeingCheckIn)
class WellBeingCheckInAdmin(admin.ModelAdmin):
    list_display = ('student', 'conducted_on', 'support_priority', 'status', 'conducted_by', 'reviewed_by')
    list_filter = ('support_priority', 'status', 'conducted_on', 'questionnaire_version')
    search_fields = ('student__first_name', 'student__last_name', 'student__learner_reference_number')
    readonly_fields = (
        'student', 'conducted_on', 'questionnaire_version', 'privacy_notice_version',
        'consent_confirmed', 'responses', 'conducted_by', 'created_at', 'updated_at',
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# Register your models here.
