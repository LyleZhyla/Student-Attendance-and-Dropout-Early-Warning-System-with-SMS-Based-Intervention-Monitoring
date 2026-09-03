from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from academics.models import ClassSchedule, GradeLevel, SchoolYear, Section, Subject
from students.models import Enrollment, Guardian, Student, StudentGuardian
from django.urls import reverse
from rest_framework.authtoken.models import Token
from audit_logs.models import AuditLog

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
        Enrollment.objects.create(
            student=cls.student, section=section, status=Enrollment.Status.ENROLLED,
            enrolled_on=school_year.starts_on,
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

    def test_student_must_be_actively_enrolled(self):
        other_student = Student.objects.create(
            learner_reference_number='123456789013', first_name='Not', last_name='Enrolled'
        )
        record = self.build_record(student=other_student)
        with self.assertRaises(ValidationError) as error:
            record.full_clean()
        self.assertIn('student', error.exception.message_dict)


class AttendanceApiTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='attendance-admin', password='Pass-4821', role=User.Role.ADMIN)
        self.teacher = User.objects.create_user(username='attendance-teacher', password='Pass-4821', role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user(username='other-teacher', password='Pass-4821', role=User.Role.TEACHER)
        self.student_user = User.objects.create_user(username='attendance-student', password='Pass-4821', role=User.Role.STUDENT)
        self.parent_user = User.objects.create_user(username='attendance-parent', password='Pass-4821', role=User.Role.PARENT)
        self.today = timezone.localdate()
        self.school_year = SchoolYear.objects.create(
            name='Current test year', starts_on=self.today - timedelta(days=90), ends_on=self.today + timedelta(days=90), is_active=True
        )
        grade = GradeLevel.objects.create(name='Grade 8', order=8)
        self.section = Section.objects.create(name='Mabini', grade_level=grade, school_year=self.school_year, adviser=self.teacher)
        subject = Subject.objects.create(code='SCI8', name='Science 8')
        self.schedule = ClassSchedule.objects.create(
            section=self.section, subject=subject, teacher=self.teacher,
            weekday=self.today.isoweekday(), starts_at=time(9), ends_at=time(10),
        )
        other_subject = Subject.objects.create(code='ENG8', name='English 8')
        self.other_schedule = ClassSchedule.objects.create(
            section=self.section, subject=other_subject, teacher=self.other_teacher,
            weekday=self.today.isoweekday(), starts_at=time(10), ends_at=time(11),
        )
        self.student = Student.objects.create(
            user=self.student_user, learner_reference_number='200000000001', first_name='Ana', last_name='Reyes'
        )
        self.outsider = Student.objects.create(
            learner_reference_number='200000000002', first_name='Ben', last_name='Santos'
        )
        Enrollment.objects.create(
            student=self.student, section=self.section, status=Enrollment.Status.ENROLLED,
            enrolled_on=self.today - timedelta(days=30),
        )
        self.guardian = Guardian.objects.create(
            user=self.parent_user, full_name='Maria Reyes', relationship='Mother', mobile_number='09170000000'
        )
        StudentGuardian.objects.create(student=self.student, guardian=self.guardian, is_primary=True)

    def auth(self, user):
        return {'HTTP_AUTHORIZATION': f'Token {Token.objects.create(user=user).key}'}

    def payload(self, status='PRESENT'):
        return {
            'schedule': self.schedule.pk, 'date': str(self.today),
            'records': [{'student': self.student.pk, 'status': status, 'time_in': '09:00', 'excuse_reason': ''}],
        }

    def create_record(self, student, record_date, status, schedule=None):
        return AttendanceRecord.objects.create(
            student=student, class_schedule=schedule or self.schedule, date=record_date,
            status=status, encoded_by=(schedule or self.schedule).teacher,
        )

    def previous_month(self):
        first = self.today.replace(day=1)
        return (first - timedelta(days=1)).replace(day=1)

    def test_teacher_only_sees_and_encodes_assigned_schedules(self):
        auth = self.auth(self.teacher)
        options = self.client.get(reverse('api-attendance-options'), **auth)
        self.assertEqual(options.status_code, 200)
        self.assertEqual([item['id'] for item in options.json()['schedules']], [self.schedule.pk])
        denied = self.client.get(
            reverse('api-attendance-roster'), {'schedule': self.other_schedule.pk, 'date': self.today}, **auth
        )
        self.assertEqual(denied.status_code, 404)

    def test_roster_contains_only_active_enrollments(self):
        response = self.client.get(
            reverse('api-attendance-roster'), {'schedule': self.schedule.pk, 'date': self.today},
            **self.auth(self.teacher),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['student'] for item in response.json()['roster']], [self.student.pk])

    def test_bulk_encoding_creates_then_corrects_and_audits(self):
        auth = self.auth(self.teacher)
        created = self.client.post(
            reverse('api-attendance-bulk'), self.payload(), content_type='application/json', **auth
        )
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json()['created'], 1)
        corrected = self.client.post(
            reverse('api-attendance-bulk'), self.payload('LATE'), content_type='application/json', **auth
        )
        self.assertEqual(corrected.status_code, 200)
        self.assertEqual(corrected.json()['updated'], 1)
        record = AttendanceRecord.objects.get(student=self.student, class_schedule=self.schedule, date=self.today)
        self.assertEqual(record.status, AttendanceRecord.Status.LATE)
        self.assertEqual(record.encoded_by, self.teacher)
        self.assertEqual(AuditLog.objects.filter(action='ATTENDANCE_BULK_ENCODED').count(), 2)

    def test_bulk_submission_is_atomic_when_student_is_not_enrolled(self):
        payload = self.payload()
        payload['records'].append({'student': self.outsider.pk, 'status': 'PRESENT'})
        response = self.client.post(
            reverse('api-attendance-bulk'), payload, content_type='application/json', **self.auth(self.teacher)
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_excused_absence_requires_reason(self):
        response = self.client.post(
            reverse('api-attendance-bulk'), self.payload('ABSENT_EXCUSED'),
            content_type='application/json', **self.auth(self.teacher),
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AttendanceRecord.objects.exists())

    def test_student_and_parent_history_is_scoped_to_linked_student(self):
        AttendanceRecord.objects.create(
            student=self.student, class_schedule=self.schedule, date=self.today,
            status=AttendanceRecord.Status.PRESENT, encoded_by=self.teacher,
        )
        AttendanceRecord.objects.create(
            student=self.outsider, class_schedule=self.schedule, date=self.today,
            status=AttendanceRecord.Status.LATE, encoded_by=self.teacher,
        )
        student_response = self.client.get(reverse('api-attendance-records'), **self.auth(self.student_user))
        parent_response = self.client.get(reverse('api-attendance-records'), **self.auth(self.parent_user))
        self.assertEqual([item['student'] for item in student_response.json()['records']], [self.student.pk])
        self.assertEqual([item['student'] for item in parent_response.json()['records']], [self.student.pk])

    def test_monthly_analytics_calculates_rates_and_six_month_trend(self):
        month = self.previous_month()
        self.create_record(self.student, month, AttendanceRecord.Status.PRESENT)
        self.create_record(self.student, month + timedelta(days=1), AttendanceRecord.Status.LATE)
        self.create_record(self.student, month + timedelta(days=2), AttendanceRecord.Status.ABSENT_UNEXCUSED)
        response = self.client.get(
            reverse('api-attendance-analytics'), {'month': month.strftime('%Y-%m')}, **self.auth(self.teacher)
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['summary']['recorded'], 3)
        self.assertEqual(payload['summary']['attendance_rate'], 66.7)
        self.assertEqual(payload['summary']['absence_rate'], 33.3)
        self.assertEqual(len(payload['monthly_trend']), 6)
        self.assertEqual(len(payload['daily_trend']), 3)
        self.assertEqual(payload['student_breakdown'][0]['monitoring_events'], 2)

    def test_school_activity_counts_as_attended_and_not_as_absent(self):
        month = self.previous_month()
        self.create_record(self.student, month, AttendanceRecord.Status.SCHOOL_ACTIVITY)
        response = self.client.get(
            reverse('api-attendance-analytics'), {'month': month.strftime('%Y-%m')}, **self.auth(self.student_user)
        )
        summary = response.json()['summary']
        self.assertEqual(summary['attendance_rate'], 100.0)
        self.assertEqual(summary['absences'], 0)

    def test_parent_analytics_only_contains_linked_children(self):
        month = self.previous_month()
        self.create_record(self.student, month, AttendanceRecord.Status.PRESENT)
        self.create_record(self.outsider, month, AttendanceRecord.Status.ABSENT_UNEXCUSED)
        response = self.client.get(
            reverse('api-attendance-analytics'), {'month': month.strftime('%Y-%m')}, **self.auth(self.parent_user)
        )
        payload = response.json()
        self.assertEqual(payload['summary']['total'], 1)
        self.assertEqual([item['student'] for item in payload['student_breakdown']], [self.student.pk])
        self.assertEqual([item['id'] for item in payload['filter_options']['students']], [self.student.pk])

    def test_teacher_cannot_filter_analytics_by_another_schedule(self):
        response = self.client.get(
            reverse('api-attendance-analytics'),
            {'month': self.today.strftime('%Y-%m'), 'schedule': self.other_schedule.pk},
            **self.auth(self.teacher),
        )
        self.assertEqual(response.status_code, 404)

    def test_future_analytics_month_is_rejected(self):
        future = (self.today.replace(day=28) + timedelta(days=5)).replace(day=1)
        response = self.client.get(
            reverse('api-attendance-analytics'), {'month': future.strftime('%Y-%m')}, **self.auth(self.admin)
        )
        self.assertEqual(response.status_code, 400)

# Create your tests here.
