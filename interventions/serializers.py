from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from .models import InterventionActivity, InterventionCase


ALLOWED_TRANSITIONS = {
    InterventionCase.Status.FOR_REVIEW: {
        InterventionCase.Status.CONTACTING_PARENT, InterventionCase.Status.CLOSED,
    },
    InterventionCase.Status.CONTACTING_PARENT: {
        InterventionCase.Status.MEETING_SCHEDULED, InterventionCase.Status.HOME_VISIT_SCHEDULED,
        InterventionCase.Status.UNDER_INTERVENTION, InterventionCase.Status.CLOSED,
    },
    InterventionCase.Status.MEETING_SCHEDULED: {
        InterventionCase.Status.CONTACTING_PARENT, InterventionCase.Status.UNDER_INTERVENTION,
    },
    InterventionCase.Status.HOME_VISIT_SCHEDULED: {
        InterventionCase.Status.CONTACTING_PARENT, InterventionCase.Status.UNDER_INTERVENTION,
    },
    InterventionCase.Status.UNDER_INTERVENTION: {
        InterventionCase.Status.FOR_FOLLOW_UP, InterventionCase.Status.RESOLVED,
    },
    InterventionCase.Status.FOR_FOLLOW_UP: {
        InterventionCase.Status.UNDER_INTERVENTION, InterventionCase.Status.RESOLVED,
    },
    InterventionCase.Status.RESOLVED: {
        InterventionCase.Status.FOR_FOLLOW_UP, InterventionCase.Status.CLOSED,
    },
    InterventionCase.Status.CLOSED: set(),
}


class InterventionCaseSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.__str__', read_only=True)
    learner_reference_number = serializers.CharField(source='student.learner_reference_number', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.__str__', read_only=True)
    created_by_name = serializers.CharField(source='created_by.__str__', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    activity_count = serializers.IntegerField(read_only=True)
    last_activity_at = serializers.DateTimeField(read_only=True)
    guardians = serializers.SerializerMethodField()

    class Meta:
        model = InterventionCase
        fields = (
            'id', 'student', 'student_name', 'learner_reference_number', 'reason', 'status', 'status_label',
            'assigned_to', 'assigned_to_name', 'scheduled_for', 'findings', 'follow_up_on',
            'created_by_name', 'activity_count', 'last_activity_at', 'created_at', 'updated_at',
            'guardians',
        )
        read_only_fields = ('created_at', 'updated_at')

    def get_guardians(self, obj):
        return [
            {'id': link.guardian_id, 'name': link.guardian.full_name, 'is_primary': link.is_primary}
            for link in obj.student.studentguardian_set.select_related('guardian').all()
        ]

    def validate_assigned_to(self, user):
        if not user.is_active or (user.role not in (User.Role.ADMIN, User.Role.TEACHER, User.Role.GUIDANCE) and not user.is_superuser):
            raise serializers.ValidationError('Assign the case to active intervention personnel.')
        return user

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance and 'student' in attrs and attrs['student'].pk != self.instance.student_id:
            raise serializers.ValidationError({'student': 'The student cannot be changed after a case is created.'})
        old_status = self.instance.status if self.instance else None
        new_status = attrs.get('status', old_status or InterventionCase.Status.FOR_REVIEW)
        if self.instance and new_status != old_status and new_status not in ALLOWED_TRANSITIONS[old_status]:
            raise serializers.ValidationError({'status': f'Cannot move a case from {self.instance.get_status_display()} to {dict(InterventionCase.Status.choices)[new_status]}.'})
        if not self.instance and new_status != InterventionCase.Status.FOR_REVIEW:
            raise serializers.ValidationError({'status': 'New cases must begin For Review.'})

        source = self.instance
        candidate = InterventionCase(
            pk=getattr(source, 'pk', None),
            student=attrs.get('student', getattr(source, 'student', None)),
            reason=attrs.get('reason', getattr(source, 'reason', '')),
            status=new_status,
            assigned_to=attrs.get('assigned_to', getattr(source, 'assigned_to', None)),
            created_by=getattr(source, 'created_by', self.context['request'].user),
            scheduled_for=attrs.get('scheduled_for', getattr(source, 'scheduled_for', None)),
            findings=attrs.get('findings', getattr(source, 'findings', '')),
            follow_up_on=attrs.get('follow_up_on', getattr(source, 'follow_up_on', None)),
        )
        candidate.full_clean(exclude=('created_at', 'updated_at'), validate_unique=False, validate_constraints=False)
        return attrs


class InterventionActivitySerializer(serializers.ModelSerializer):
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)
    activity_type_label = serializers.CharField(source='get_activity_type_display', read_only=True)
    channel_label = serializers.CharField(source='get_channel_display', read_only=True)
    outcome_label = serializers.CharField(source='get_outcome_display', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.__str__', read_only=True)

    class Meta:
        model = InterventionActivity
        fields = (
            'id', 'activity_type', 'activity_type_label', 'guardian', 'guardian_name', 'channel',
            'channel_label', 'outcome', 'outcome_label', 'notes', 'occurred_at', 'next_action_on',
            'recorded_by_name', 'created_at',
        )
        read_only_fields = ('created_at',)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        case = self.context['case']
        candidate = InterventionActivity(
            case=case,
            activity_type=attrs.get('activity_type'),
            guardian=attrs.get('guardian'),
            channel=attrs.get('channel', ''),
            outcome=attrs.get('outcome', ''),
            notes=attrs.get('notes', ''),
            occurred_at=attrs.get('occurred_at', timezone.now()),
            next_action_on=attrs.get('next_action_on'),
            recorded_by=self.context['request'].user,
        )
        candidate.full_clean(exclude=('created_at',), validate_unique=False, validate_constraints=False)
        return attrs
