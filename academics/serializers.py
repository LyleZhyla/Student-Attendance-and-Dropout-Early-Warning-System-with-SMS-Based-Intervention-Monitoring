from rest_framework import serializers

from accounts.models import User
from .models import ClassSchedule, GradeLevel, SchoolYear, Section, Subject


class ValidatedModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance or self.Meta.model()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean(exclude=[field.name for field in instance._meta.fields if field.name not in attrs and not instance.pk])
        return attrs


class SchoolYearSerializer(ValidatedModelSerializer):
    class Meta:
        model = SchoolYear
        fields = ('id', 'name', 'starts_on', 'ends_on', 'is_active')


class GradeLevelSerializer(ValidatedModelSerializer):
    class Meta:
        model = GradeLevel
        fields = ('id', 'name', 'order')


class SubjectSerializer(ValidatedModelSerializer):
    class Meta:
        model = Subject
        fields = ('id', 'code', 'name')


class SectionSerializer(ValidatedModelSerializer):
    grade_level_name = serializers.CharField(source='grade_level.name', read_only=True)
    school_year_name = serializers.CharField(source='school_year.name', read_only=True)
    adviser_name = serializers.CharField(source='adviser.__str__', read_only=True)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Section
        fields = (
            'id', 'name', 'grade_level', 'grade_level_name', 'school_year', 'school_year_name',
            'adviser', 'adviser_name', 'student_count',
        )

    def validate_adviser(self, adviser):
        if adviser.role != User.Role.TEACHER or not adviser.is_active:
            raise serializers.ValidationError('Choose an active Teacher account.')
        return adviser


class ClassScheduleSerializer(ValidatedModelSerializer):
    section_name = serializers.CharField(source='section.__str__', read_only=True)
    subject_name = serializers.CharField(source='subject.__str__', read_only=True)
    teacher_name = serializers.CharField(source='teacher.__str__', read_only=True)
    weekday_label = serializers.CharField(source='get_weekday_display', read_only=True)

    class Meta:
        model = ClassSchedule
        fields = (
            'id', 'section', 'section_name', 'subject', 'subject_name', 'teacher', 'teacher_name',
            'weekday', 'weekday_label', 'starts_at', 'ends_at',
        )

    def validate_teacher(self, teacher):
        if teacher.role != User.Role.TEACHER or not teacher.is_active:
            raise serializers.ValidationError('Choose an active Teacher account.')
        return teacher
