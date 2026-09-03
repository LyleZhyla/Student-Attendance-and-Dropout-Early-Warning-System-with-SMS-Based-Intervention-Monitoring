from django.contrib import admin

from .models import InterventionActivity, InterventionCase


class InterventionActivityInline(admin.TabularInline):
    model = InterventionActivity
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(InterventionCase)
class InterventionCaseAdmin(admin.ModelAdmin):
    list_display = ('student', 'status', 'assigned_to', 'scheduled_for', 'follow_up_on', 'updated_at')
    list_filter = ('status', 'assigned_to')
    search_fields = ('student__first_name', 'student__last_name', 'student__learner_reference_number', 'reason')
    inlines = (InterventionActivityInline,)


@admin.register(InterventionActivity)
class InterventionActivityAdmin(admin.ModelAdmin):
    list_display = ('case', 'activity_type', 'guardian', 'outcome', 'occurred_at', 'recorded_by')
    list_filter = ('activity_type', 'channel', 'outcome')

# Register your models here.
