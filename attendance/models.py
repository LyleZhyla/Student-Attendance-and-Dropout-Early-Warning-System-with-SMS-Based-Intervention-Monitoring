from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = 'PRESENT', 'Present'
        LATE = 'LATE', 'Late'
        ABSENT_EXCUSED = 'ABSENT_EXCUSED', 'Excused Absence'
        ABSENT_UNEXCUSED = 'ABSENT_UNEXCUSED', 'Unexcused Absence'
        SCHOOL_ACTIVITY = 'SCHOOL_ACTIVITY', 'School Activity'
        NOT_RECORDED = 'NOT_RECORDED', 'Not Recorded'

    student = models.ForeignKey('students.Student', on_delete=models.PROTECT, related_name='attendance_records')
    class_schedule = models.ForeignKey('academics.ClassSchedule', on_delete=models.PROTECT, related_name='attendance_records')
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.NOT_RECORDED, db_index=True)
    time_in = models.TimeField(null=True, blank=True)
    excuse_reason = models.TextField(blank=True)
    encoded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='encoded_attendance')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-date', 'student__last_name')
        constraints = [models.UniqueConstraint(fields=('student', 'class_schedule', 'date'), name='unique_student_schedule_attendance')]

    def clean(self):
        errors = {}
        if self.date and self.date > timezone.localdate():
            errors['date'] = 'Attendance cannot be recorded for a future date.'
        if self.status == self.Status.ABSENT_EXCUSED and not self.excuse_reason.strip():
            errors['excuse_reason'] = 'A reason is required for an excused absence.'
        if self.student_id and self.class_schedule_id and self.date:
            from students.models import Enrollment

            schedule = self.class_schedule
            if not schedule.section.school_year.starts_on <= self.date <= schedule.section.school_year.ends_on:
                errors['date'] = 'Attendance date must be within the schedule school year.'
            elif self.date.isoweekday() != schedule.weekday:
                errors['date'] = f'This class is scheduled on {schedule.get_weekday_display()}.'
            enrolled = Enrollment.objects.filter(
                student_id=self.student_id,
                section_id=schedule.section_id,
                status=Enrollment.Status.ENROLLED,
                enrolled_on__lte=self.date,
                student__is_active=True,
            ).exists()
            if not enrolled:
                errors['student'] = 'The student is not actively enrolled in this schedule section on this date.'
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f'{self.student} - {self.date} - {self.get_status_display()}'

# Create your models here.
