from django.contrib import admin

from .models import SMSLog

@admin.register(SMSLog)
class SMSLogAdmin(admin.ModelAdmin):
    list_display = ('student', 'guardian', 'category', 'recipient_masked', 'status', 'retry_count', 'queued_at')
    list_filter = ('category', 'status', 'queued_at')
    search_fields = ('student__first_name', 'student__last_name', 'guardian__full_name', 'event_key')
    readonly_fields = (
        'recipient_masked', 'provider_reference', 'retry_count', 'error_message', 'queued_at',
        'last_attempted_at', 'sent_at', 'delivered_at', 'updated_at',
    )

# Register your models here.
