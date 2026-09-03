from datetime import date, time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token

from audit_logs.models import AuditLog
from .models import ClassSchedule, GradeLevel, SchoolYear, Section, Subject


class AcademicMasterDataTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin3', password='Pass-4821-test', role=User.Role.ADMIN)
        self.teacher = User.objects.create_user(username='teacher3', password='Pass-4821-test', role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user(username='teacher4', password='Pass-4821-test', role=User.Role.TEACHER)
        self.admin_auth = {'HTTP_AUTHORIZATION': f'Token {Token.objects.create(user=self.admin).key}'}
        self.teacher_auth = {'HTTP_AUTHORIZATION': f'Token {Token.objects.create(user=self.teacher).key}'}

    def test_only_admin_can_manage_academic_data(self):
        response = self.client.get(reverse('api-grade-levels'), **self.teacher_auth)
        self.assertEqual(response.status_code, 403)

    def test_admin_builds_academic_structure_and_audit_is_written(self):
        response = self.client.post(
            reverse('api-school-years'),
            {'name': '2026-2027', 'starts_on': '2026-06-01', 'ends_on': '2027-03-31', 'is_active': True},
            content_type='application/json', **self.admin_auth,
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(SchoolYear.objects.get(name='2026-2027').is_active)
        self.assertTrue(AuditLog.objects.filter(action='MASTER_DATA_CREATED', object_type='academics.SchoolYear').exists())

    def test_activating_school_year_deactivates_previous_one(self):
        first = SchoolYear.objects.create(name='2025-2026', starts_on=date(2025, 6, 1), ends_on=date(2026, 3, 31), is_active=True)
        second = SchoolYear.objects.create(name='2026-2027', starts_on=date(2026, 6, 1), ends_on=date(2027, 3, 31), is_active=True)
        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)

    def test_overlapping_section_schedule_is_rejected(self):
        year = SchoolYear.objects.create(name='2026-2027', starts_on=date(2026, 6, 1), ends_on=date(2027, 3, 31))
        grade = GradeLevel.objects.create(name='Grade 7', order=7)
        subject = Subject.objects.create(code='MATH7', name='Mathematics 7')
        section = Section.objects.create(name='Rizal', grade_level=grade, school_year=year, adviser=self.teacher)
        ClassSchedule.objects.create(
            section=section, subject=subject, teacher=self.teacher, weekday=1,
            starts_at=time(8), ends_at=time(9),
        )
        response = self.client.post(
            reverse('api-schedules'),
            {'section': section.pk, 'subject': subject.pk, 'teacher': self.other_teacher.pk, 'weekday': 1, 'starts_at': '08:30', 'ends_at': '09:30'},
            content_type='application/json', **self.admin_auth,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('overlaps', str(response.json()))

# Create your tests here.
