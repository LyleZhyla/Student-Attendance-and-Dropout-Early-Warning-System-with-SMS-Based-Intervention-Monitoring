from rest_framework import serializers

from .models import RiskAssessment


class RiskAssessmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.__str__', read_only=True)
    learner_reference_number = serializers.CharField(source='student.learner_reference_number', read_only=True)
    level_label = serializers.CharField(source='get_level_display', read_only=True)
    review_decision_label = serializers.CharField(source='get_review_decision_display', read_only=True)
    generated_by_name = serializers.CharField(source='generated_by.__str__', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.__str__', read_only=True)
    reviewer_notes = serializers.SerializerMethodField()

    class Meta:
        model = RiskAssessment
        fields = (
            'id', 'student', 'student_name', 'learner_reference_number', 'score', 'level', 'level_label',
            'indicators', 'policy_version', 'period_start', 'period_end', 'assessed_on',
            'review_decision', 'review_decision_label', 'reviewer_notes', 'generated_by_name',
            'reviewed_by_name', 'reviewed_at', 'created_at', 'updated_at',
        )

    def get_reviewer_notes(self, obj):
        request = self.context.get('request')
        if request and not request.user.is_superuser and request.user.role == request.user.Role.TEACHER:
            return ''
        return obj.reviewer_notes


class GenerateAssessmentSerializer(serializers.Serializer):
    student = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    assessed_on = serializers.DateField(required=False)


class ReviewAssessmentSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=(
        RiskAssessment.ReviewDecision.CONFIRMED,
        RiskAssessment.ReviewDecision.DISMISSED,
        RiskAssessment.ReviewDecision.NEEDS_MORE_INFO,
    ))
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)

    def validate(self, attrs):
        if attrs['decision'] in (
            RiskAssessment.ReviewDecision.DISMISSED,
            RiskAssessment.ReviewDecision.NEEDS_MORE_INFO,
        ) and not attrs.get('notes', '').strip():
            raise serializers.ValidationError({'notes': 'Reviewer notes are required for this decision.'})
        return attrs
