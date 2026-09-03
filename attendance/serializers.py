from rest_framework import serializers

from .models import AttendanceRecord


class AttendanceRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.__str__', read_only=True)
    learner_reference_number = serializers.CharField(source='student.learner_reference_number', read_only=True)
    schedule_name = serializers.CharField(source='class_schedule.__str__', read_only=True)
    section_name = serializers.CharField(source='class_schedule.section.__str__', read_only=True)
    subject_name = serializers.CharField(source='class_schedule.subject.__str__', read_only=True)
    encoder_name = serializers.CharField(source='encoded_by.__str__', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AttendanceRecord
        fields = (
            'id', 'student', 'student_name', 'learner_reference_number', 'class_schedule',
            'schedule_name', 'section_name', 'subject_name', 'date', 'status', 'status_label',
            'time_in', 'excuse_reason', 'encoded_by', 'encoder_name', 'created_at', 'updated_at',
        )
        read_only_fields = ('encoded_by',)


class AttendanceEntrySerializer(serializers.Serializer):
    student = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=AttendanceRecord.Status.choices)
    time_in = serializers.TimeField(required=False, allow_null=True)
    excuse_reason = serializers.CharField(required=False, allow_blank=True, trim_whitespace=True)

    def validate(self, attrs):
        if attrs['status'] == AttendanceRecord.Status.ABSENT_EXCUSED and not attrs.get('excuse_reason', ''):
            raise serializers.ValidationError({'excuse_reason': 'A reason is required for an excused absence.'})
        return attrs
