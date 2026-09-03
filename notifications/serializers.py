from rest_framework import serializers

from .models import SMSLog


class SMSLogSerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    student_name = serializers.CharField(source='student.__str__', read_only=True)
    category_label = serializers.CharField(source='get_category_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.__str__', read_only=True)

    class Meta:
        model = SMSLog
        fields = (
            'id', 'guardian', 'guardian_name', 'student', 'student_name', 'category', 'category_label',
            'message', 'recipient_masked', 'event_key', 'status', 'status_label', 'provider_reference',
            'retry_count', 'error_message', 'created_by_name', 'queued_at', 'last_attempted_at',
            'sent_at', 'delivered_at', 'updated_at',
        )


class SMSCreateSerializer(serializers.Serializer):
    student = serializers.IntegerField(min_value=1)
    guardian = serializers.IntegerField(min_value=1)
    category = serializers.ChoiceField(choices=SMSLog.Category.choices)
    message = serializers.CharField(max_length=480, trim_whitespace=True)
    event_key = serializers.RegexField(r'^[A-Za-z0-9][A-Za-z0-9:._-]{2,149}$')

    def validate_message(self, value):
        if not value.strip():
            raise serializers.ValidationError('Message cannot be blank.')
        return value.strip()
