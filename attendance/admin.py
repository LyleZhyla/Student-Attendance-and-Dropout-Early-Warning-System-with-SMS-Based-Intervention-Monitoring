from django.contrib import admin

from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'class_schedule', 'status', 'encoded_by')
    list_filter = ('status', 'date')
    search_fields = ('student__first_name', 'student__last_name', 'student__learner_reference_number')

# Register your models here.
