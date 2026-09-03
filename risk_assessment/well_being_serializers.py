from django.utils import timezone
from rest_framework import serializers

from .models import WellBeingCheckIn
from .well_being import PRIVACY_NOTICE_VERSION, QUESTIONNAIRE_VERSION, validate_responses


class WellBeingSummarySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.__str__', read_only=True)
    learner_reference_number = serializers.CharField(source='student.learner_reference_number', read_only=True)
    support_priority_label = serializers.CharField(source='get_support_priority_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    conducted_by_name = serializers.CharField(source='conducted_by.__str__', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.__str__', read_only=True)

    class Meta:
        model = WellBeingCheckIn
        fields = (
            'id', 'student', 'student_name', 'learner_reference_number', 'conducted_on',
            'questionnaire_version', 'support_priority', 'support_priority_label', 'status', 'status_label',
            'conducted_by_name', 'reviewed_by_name', 'reviewed_at', 'created_at', 'updated_at',
        )


class WellBeingDetailSerializer(WellBeingSummarySerializer):
    class Meta(WellBeingSummarySerializer.Meta):
        fields = WellBeingSummarySerializer.Meta.fields + (
            'privacy_notice_version', 'consent_confirmed', 'responses', 'private_notes', 'recommended_actions',
        )


class WellBeingCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = WellBeingCheckIn
        fields = (
            'student', 'conducted_on', 'privacy_notice_version', 'consent_confirmed', 'responses',
            'support_priority', 'private_notes', 'recommended_actions',
        )
        validators = []

    def validate(self, attrs):
        attrs = super().validate(attrs)
        response_errors = validate_responses(attrs.get('responses'))
        if response_errors:
            raise serializers.ValidationError(response_errors)
        if attrs.get('privacy_notice_version') != PRIVACY_NOTICE_VERSION:
            raise serializers.ValidationError({'privacy_notice_version': 'Use the current well-being privacy notice.'})
        candidate = WellBeingCheckIn(
            **attrs,
            questionnaire_version=QUESTIONNAIRE_VERSION,
            status=WellBeingCheckIn.Status.OPEN,
            conducted_by=self.context['request'].user,
        )
        candidate.full_clean(
            exclude=('reviewed_by', 'reviewed_at', 'created_at', 'updated_at'),
            validate_unique=False, validate_constraints=False,
        )
        return attrs


class WellBeingUpdateSerializer(serializers.Serializer):
    support_priority = serializers.ChoiceField(choices=WellBeingCheckIn.SupportPriority.choices, required=False)
    status = serializers.ChoiceField(choices=WellBeingCheckIn.Status.choices, required=False)
    private_notes = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    recommended_actions = serializers.CharField(required=False, allow_blank=True, max_length=5000)

    def validate(self, attrs):
        instance = self.context['instance']
        if instance.status == WellBeingCheckIn.Status.CLOSED:
            raise serializers.ValidationError({'status': 'Closed check-ins are immutable.'})
        new_status = attrs.get('status', instance.status)
        allowed = {
            WellBeingCheckIn.Status.OPEN: {WellBeingCheckIn.Status.OPEN, WellBeingCheckIn.Status.ACTION_PLANNED, WellBeingCheckIn.Status.CLOSED},
            WellBeingCheckIn.Status.ACTION_PLANNED: {WellBeingCheckIn.Status.ACTION_PLANNED, WellBeingCheckIn.Status.CLOSED},
            WellBeingCheckIn.Status.CLOSED: {WellBeingCheckIn.Status.CLOSED},
        }
        if new_status not in allowed[instance.status]:
            raise serializers.ValidationError({'status': 'This well-being status transition is not allowed.'})
        reviewer = self.context['request'].user if new_status != WellBeingCheckIn.Status.OPEN else None
        reviewed_at = timezone.now() if reviewer else None
        candidate = WellBeingCheckIn(
            pk=instance.pk, student=instance.student, conducted_on=instance.conducted_on,
            questionnaire_version=instance.questionnaire_version,
            privacy_notice_version=instance.privacy_notice_version,
            consent_confirmed=instance.consent_confirmed, responses=instance.responses,
            conducted_by=instance.conducted_by,
            support_priority=attrs.get('support_priority', instance.support_priority),
            status=new_status,
            private_notes=attrs.get('private_notes', instance.private_notes),
            recommended_actions=attrs.get('recommended_actions', instance.recommended_actions),
            reviewed_by=reviewer or instance.reviewed_by,
            reviewed_at=reviewed_at or instance.reviewed_at,
        )
        candidate.full_clean(exclude=('created_at', 'updated_at'), validate_unique=False, validate_constraints=False)
        return attrs
