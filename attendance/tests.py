from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from academics.models import ClassSchedule, GradeLevel, SchoolYear, Section, Subject
from students.models import Student

from .models import AttendanceRecord


class AttendanceRecordTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.teacher = get_user_model().objects.create_user(
            username='teacher', password='test-password', role='TEACHER'
        )
        school_year = SchoolYear.objects.create(
            name='2026-2027', starts_on=date(2026, 6, 1), ends_on=date(2027, 3, 31)
        )
        grade = GradeLevel.objects.create(name='Grade 10', order=10)
        section = Section.objects.create(
            name='Rizal', grade_level=grade, school_year=school_year, adviser=cls.teacher
        )
        subject = Subject.objects.create(code='MATH10', name='Mathematics 10')
        cls.schedule = ClassSchedule.objects.create(
            section=section, subject=subject, teacher=cls.teacher,
            weekday=ClassSchedule.Weekday.MONDAY, starts_at=time(8), ends_at=time(9)
        )
        cls.student = Student.objects.create(
            learner_reference_number='123456789012', first_name='Sample', last_name='Student'
        )

    def build_record(self, **overrides):
        values = {
            'student': self.student,
            'class_schedule': self.schedule,
            'date': timezone.localdate(),
            'status': AttendanceRecord.Status.PRESENT,
            'encoded_by': self.teacher,
        }
        values.update(overrides)
        return AttendanceRecord(**values)

    def test_future_attendance_is_rejected(self):
        record = self.build_record(date=timezone.localdate() + timedelta(days=1))
        with self.assertRaises(ValidationError) as error:
            record.full_clean()
        self.assertIn('date', error.exception.message_dict)

    def test_excused_absence_requires_reason(self):
        record = self.build_record(status=AttendanceRecord.Status.ABSENT_EXCUSED)
        with self.assertRaises(ValidationError) as error:
            record.full_clean()
        self.assertIn('excuse_reason', error.exception.message_dict)

    def test_duplicate_student_schedule_date_is_rejected(self):
        self.build_record().save()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.build_record().save()

# Create your tests here.
