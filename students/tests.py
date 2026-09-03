from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token

from academics.models import GradeLevel, SchoolYear, Section
from audit_logs.models import AuditLog
from .models import Enrollment, Guardian, Student, StudentGuardian


class StudentMasterDataTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin-students', password='Pass-4821-test', role=User.Role.ADMIN)
        self.teacher = User.objects.create_user(username='adviser', password='Pass-4821-test', role=User.Role.TEACHER)
        self.student_user = User.objects.create_user(username='student-user', password='Pass-4821-test', role=User.Role.STUDENT)
        self.parent_user = User.objects.create_user(username='parent-user', password='Pass-4821-test', role=User.Role.PARENT)
        self.auth = {'HTTP_AUTHORIZATION': f'Token {Token.objects.create(user=self.admin).key}'}
        year = SchoolYear.objects.create(name='2026-2027', starts_on=date(2026, 6, 1), ends_on=date(2027, 3, 31))
        grade = GradeLevel.objects.create(name='Grade 8', order=8)
        self.section_a = Section.objects.create(name='A', grade_level=grade, school_year=year, adviser=self.teacher)
        self.section_b = Section.objects.create(name='B', grade_level=grade, school_year=year, adviser=self.teacher)

    def test_admin_creates_student_with_student_account(self):
        response = self.client.post(
            reverse('api-students'),
            {'learner_reference_number': '123456789012', 'first_name': 'Juan', 'middle_name': '', 'last_name': 'Dela Cruz', 'user': self.student_user.pk, 'is_active': True},
            content_type='application/json', **self.auth,
        )
        self.assertEqual(response.status_code, 201)
        student = Student.objects.get(learner_reference_number='123456789012')
        self.assertEqual(student.user, self.student_user)
        self.assertTrue(AuditLog.objects.filter(action='MASTER_DATA_CREATED', object_type='students.Student').exists())

    def test_parent_account_cannot_be_assigned_to_student(self):
        response = self.client.post(
            reverse('api-students'),
            {'learner_reference_number': '123456789013', 'first_name': 'Maria', 'last_name': 'Santos', 'user': self.parent_user.pk},
            content_type='application/json', **self.auth,
        )
        self.assertEqual(response.status_code, 400)

    def test_only_one_active_enrollment_per_school_year(self):
        student = Student.objects.create(learner_reference_number='123456789014', first_name='Ana', last_name='Reyes')
        Enrollment.objects.create(student=student, section=self.section_a, status=Enrollment.Status.ENROLLED, enrolled_on=date(2026, 6, 1))
        response = self.client.post(
            reverse('api-enrollments'),
            {'student': student.pk, 'section': self.section_b.pk, 'status': 'ENROLLED', 'enrolled_on': '2026-06-01'},
            content_type='application/json', **self.auth,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('already has an active enrollment', str(response.json()))

    def test_only_one_primary_guardian_per_student(self):
        student = Student.objects.create(learner_reference_number='123456789015', first_name='Liza', last_name='Cruz')
        first = Guardian.objects.create(full_name='Parent One', relationship='Mother', mobile_number='09170000001')
        second = Guardian.objects.create(full_name='Parent Two', relationship='Father', mobile_number='09170000002')
        StudentGuardian.objects.create(student=student, guardian=first, is_primary=True)
        response = self.client.post(
            reverse('api-student-guardian-links'),
            {'student': student.pk, 'guardian': second.pk, 'is_primary': True},
            content_type='application/json', **self.auth,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('primary guardian', str(response.json()))

# Create your tests here.
