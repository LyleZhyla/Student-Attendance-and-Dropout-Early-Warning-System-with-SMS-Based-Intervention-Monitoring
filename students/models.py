from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Guardian(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='guardian_profile')
    full_name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=50)
    mobile_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    sms_consent = models.BooleanField(default=False)

    def __str__(self):
        return self.full_name

    def clean(self):
        if self.user_id and self.user.role != self.user.Role.PARENT:
            raise ValidationError({'user': 'A guardian profile can only use a Parent/Guardian account.'})


class Student(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='student_profile')
    learner_reference_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80)
    birth_date = models.DateField(null=True, blank=True)
    address = models.TextField(blank=True)
    guardians = models.ManyToManyField(Guardian, through='StudentGuardian', related_name='students')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('last_name', 'first_name')

    def __str__(self):
        return f'{self.last_name}, {self.first_name}'

    def clean(self):
        if self.user_id and self.user.role != self.user.Role.STUDENT:
            raise ValidationError({'user': 'A student profile can only use a Student account.'})


class StudentGuardian(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE)
    is_primary = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('student', 'guardian'), name='unique_student_guardian'),
            models.UniqueConstraint(
                fields=('student',), condition=models.Q(is_primary=True), name='unique_primary_guardian_per_student'
            ),
        ]


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ENROLLED = 'ENROLLED', 'Enrolled'
        TRANSFERRED = 'TRANSFERRED', 'Transferred'
        COMPLETED = 'COMPLETED', 'Completed'
        DROPPED = 'DROPPED', 'Dropped'

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='enrollments')
    section = models.ForeignKey('academics.Section', on_delete=models.PROTECT, related_name='enrollments')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ENROLLED)
    enrolled_on = models.DateField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=('student', 'section'), name='unique_student_section_enrollment')]

    def __str__(self):
        return f'{self.student} / {self.section}'

    def clean(self):
        if self.student_id and not self.student.is_active and self.status == self.Status.ENROLLED:
            raise ValidationError({'student': 'An inactive student cannot have an active enrollment.'})

# Create your models here.
