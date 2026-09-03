from rest_framework import serializers

from accounts.models import User
from .models import Enrollment, Guardian, Student, StudentGuardian


class ValidatedModelSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance or self.Meta.model()
        for field, value in attrs.items():
            setattr(instance, field, value)
        instance.full_clean(exclude=[field.name for field in instance._meta.fields if field.name not in attrs and not instance.pk])
        return attrs


class StudentSerializer(ValidatedModelSerializer):
    full_name = serializers.SerializerMethodField()
    account_name = serializers.CharField(source='user.__str__', read_only=True)
    current_section = serializers.SerializerMethodField()
    guardians = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = (
            'id', 'learner_reference_number', 'first_name', 'middle_name', 'last_name', 'full_name',
            'birth_date', 'address', 'user', 'account_name', 'is_active', 'current_section', 'guardians',
        )

    def get_full_name(self, obj):
        return ' '.join(part for part in (obj.first_name, obj.middle_name, obj.last_name) if part)

    def get_current_section(self, obj):
        enrollment = obj.enrollments.filter(status=Enrollment.Status.ENROLLED).select_related('section__grade_level').first()
        return enrollment.section.__str__() if enrollment else None

    def get_guardians(self, obj):
        links = obj.studentguardian_set.select_related('guardian').all()
        return [{'id': link.guardian_id, 'full_name': link.guardian.full_name, 'is_primary': link.is_primary} for link in links]

    def validate_user(self, user):
        if user and (user.role != User.Role.STUDENT or not user.is_active):
            raise serializers.ValidationError('Choose an active Student account.')
        return user


class GuardianSerializer(ValidatedModelSerializer):
    account_name = serializers.CharField(source='user.__str__', read_only=True)
    student_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Guardian
        fields = (
            'id', 'full_name', 'relationship', 'mobile_number', 'email', 'address',
            'sms_consent', 'mobile_verified', 'user', 'account_name', 'student_count',
        )

    def validate_user(self, user):
        if user and (user.role != User.Role.PARENT or not user.is_active):
            raise serializers.ValidationError('Choose an active Parent/Guardian account.')
        return user

    def update(self, instance, validated_data):
        if (
            'mobile_number' in validated_data
            and validated_data['mobile_number'] != instance.mobile_number
            and 'mobile_verified' not in validated_data
        ):
            validated_data['mobile_verified'] = False
        return super().update(instance, validated_data)


class EnrollmentSerializer(ValidatedModelSerializer):
    student_name = serializers.CharField(source='student.__str__', read_only=True)
    section_name = serializers.CharField(source='section.__str__', read_only=True)
    school_year_name = serializers.CharField(source='section.school_year.name', read_only=True)

    class Meta:
        model = Enrollment
        fields = (
            'id', 'student', 'student_name', 'section', 'section_name', 'school_year_name',
            'status', 'enrolled_on',
        )

    def validate(self, attrs):
        attrs = super().validate(attrs)
        student = attrs.get('student', getattr(self.instance, 'student', None))
        section = attrs.get('section', getattr(self.instance, 'section', None))
        status = attrs.get('status', getattr(self.instance, 'status', Enrollment.Status.ENROLLED))
        if student and section and status == Enrollment.Status.ENROLLED:
            duplicate = Enrollment.objects.exclude(pk=getattr(self.instance, 'pk', None)).filter(
                student=student, section__school_year=section.school_year, status=Enrollment.Status.ENROLLED
            )
            if duplicate.exists():
                raise serializers.ValidationError({'section': 'The student already has an active enrollment for this school year.'})
        return attrs


class StudentGuardianSerializer(ValidatedModelSerializer):
    student_name = serializers.CharField(source='student.__str__', read_only=True)
    guardian_name = serializers.CharField(source='guardian.full_name', read_only=True)

    class Meta:
        model = StudentGuardian
        fields = ('id', 'student', 'student_name', 'guardian', 'guardian_name', 'is_primary')

    def validate(self, attrs):
        student = attrs.get('student', getattr(self.instance, 'student', None))
        if attrs.get('is_primary', getattr(self.instance, 'is_primary', False)):
            existing = StudentGuardian.objects.exclude(pk=getattr(self.instance, 'pk', None)).filter(
                student=student, is_primary=True
            )
            if existing.exists():
                raise serializers.ValidationError({'is_primary': 'This student already has a primary guardian.'})
        return super().validate(attrs)
