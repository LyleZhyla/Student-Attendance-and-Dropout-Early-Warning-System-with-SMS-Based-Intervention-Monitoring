from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class SchoolYear(models.Model):
    name = models.CharField(max_length=20, unique=True, help_text='Example: 2026-2027')
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_active = models.BooleanField(default=False)

    def clean(self):
        if self.starts_on and self.ends_on and self.ends_on <= self.starts_on:
            raise ValidationError({'ends_on': 'End date must be after the start date.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.is_active:
            SchoolYear.objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)
        return super().save(*args, **kwargs)

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

    def clean(self):
        if self.adviser_id and self.adviser.role != self.adviser.Role.TEACHER:
            raise ValidationError({'adviser': 'The section adviser must have the Teacher role.'})


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
        errors = {}
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            errors['ends_at'] = 'End time must be after the start time.'
        if self.teacher_id and self.teacher.role != self.teacher.Role.TEACHER:
            errors['teacher'] = 'The assigned class teacher must have the Teacher role.'
        if self.section_id and self.weekday and self.starts_at and self.ends_at:
            overlap = ClassSchedule.objects.exclude(pk=self.pk).filter(
                section_id=self.section_id,
                weekday=self.weekday,
                starts_at__lt=self.ends_at,
                ends_at__gt=self.starts_at,
            )
            if overlap.exists():
                errors['starts_at'] = 'This schedule overlaps another class in the section.'
        if self.teacher_id and self.weekday and self.starts_at and self.ends_at:
            teacher_overlap = ClassSchedule.objects.exclude(pk=self.pk).filter(
                teacher_id=self.teacher_id,
                weekday=self.weekday,
                starts_at__lt=self.ends_at,
                ends_at__gt=self.starts_at,
            )
            if teacher_overlap.exists():
                errors['teacher'] = 'The teacher already has an overlapping class schedule.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.subject.code} / {self.section}'

# Create your models here.
