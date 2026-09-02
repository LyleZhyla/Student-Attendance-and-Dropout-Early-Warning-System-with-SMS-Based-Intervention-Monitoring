from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class SchoolYear(models.Model):
    name = models.CharField(max_length=20, unique=True, help_text='Example: 2026-2027')
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_active = models.BooleanField(default=False)

    def clean(self):
        if self.ends_on <= self.starts_on:
            raise ValidationError({'ends_on': 'End date must be after the start date.'})

    def __str__(self):
        return self.name


class GradeLevel(models.Model):
    name = models.CharField(max_length=50, unique=True)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ('order', 'name')

    def __str__(self):
        return self.name


class Section(models.Model):
    name = models.CharField(max_length=100)
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.PROTECT, related_name='sections')
    school_year = models.ForeignKey(SchoolYear, on_delete=models.PROTECT, related_name='sections')
    adviser = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='advised_sections')

    class Meta:
        constraints = [models.UniqueConstraint(fields=('name', 'grade_level', 'school_year'), name='unique_section_per_year')]

    def __str__(self):
        return f'{self.grade_level} - {self.name}'


class Subject(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)

    def __str__(self):
        return f'{self.code} - {self.name}'


class ClassSchedule(models.Model):
    class Weekday(models.IntegerChoices):
        MONDAY = 1, 'Monday'
        TUESDAY = 2, 'Tuesday'
        WEDNESDAY = 3, 'Wednesday'
        THURSDAY = 4, 'Thursday'
        FRIDAY = 5, 'Friday'
        SATURDAY = 6, 'Saturday'

    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='schedules')
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name='schedules')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='class_schedules')
    weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
    starts_at = models.TimeField()
    ends_at = models.TimeField()

    def clean(self):
        if self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'End time must be after the start time.'})

    def __str__(self):
        return f'{self.subject.code} / {self.section}'

# Create your models here.
