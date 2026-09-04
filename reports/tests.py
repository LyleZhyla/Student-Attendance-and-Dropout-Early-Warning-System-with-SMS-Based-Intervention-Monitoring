from datetime import timedelta, time
from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User
from academics.models import SchoolYear, GradeLevel, Section, Subject, ClassSchedule
from attendance.models import AttendanceRecord
from interventions.models import InterventionCase
from risk_assessment.models import RiskAssessment
from audit_logs.models import AuditLog
from students.models import Student


class ReportTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(username='report-admin', role='ADMIN')
        self.guidance = User.objects.create_user(username='report-guidance', role='GUIDANCE')
        self.teacher = User.objects.create_user(username='report-teacher', role='TEACHER')
        self.student = Student.objects.create(first_name='<script>alert(1)</script>', last_name='Report', learner_reference_number='001')
        self.other = Student.objects.create(first_name='Other', last_name='Student', learner_reference_number='002')
        self.today = timezone.localdate()
        self.filters = {'kind': 'attendance', 'start': str(self.today), 'end': str(self.today)}
        self.client.force_authenticate(self.admin)
        year = SchoolYear.objects.create(name='Report year', starts_on=self.today - timedelta(days=30), ends_on=self.today + timedelta(days=100))
        grade = GradeLevel.objects.create(name='Report grade')
        section = Section.objects.create(name='A', grade_level=grade, school_year=year, adviser=self.teacher)
        subject = Subject.objects.create(code='REPORT', name='Report subject')
        self.schedule = ClassSchedule.objects.create(section=section, subject=subject, teacher=self.teacher, weekday=1, starts_at=time(8), ends_at=time(9))

    def attendance(self, student=None, day=None):
        return AttendanceRecord.objects.create(student=student or self.student, class_schedule=self.schedule, date=day or self.today, status='ABSENT_EXCUSED', excuse_reason='SECRET-EXCUSE', encoded_by=self.teacher)

    def test_unauthorized_roles_and_anonymous(self):
        for role in ('TEACHER', 'STUDENT', 'PARENT'):
            self.client.force_authenticate(User.objects.create_user(username=f'report-{role}', role=role))
            for endpoint in ('api-report-options', 'api-report-preview', 'api-audit-logs'):
                self.assertEqual(self.client.get(reverse(endpoint), self.filters).status_code, 403)
            self.assertEqual(self.client.post(reverse('api-report-print'), self.filters).status_code, 403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(reverse('api-report-preview'), self.filters).status_code, 401)

    def test_guidance_reports_but_not_audit(self):
        self.client.force_authenticate(self.guidance)
        self.assertEqual(self.client.get(reverse('api-report-preview'), self.filters).status_code, 200)
        self.assertEqual(self.client.get(reverse('api-audit-logs')).status_code, 403)
        self.assertFalse(self.client.get(reverse('api-report-options')).data['can_view_audit'])

    def test_attendance_filters_and_privacy(self):
        self.attendance()
        self.attendance(self.other)
        self.attendance(day=self.today - timedelta(days=1))
        response = self.client.get(reverse('api-report-preview'), {**self.filters, 'student': self.student.pk})
        self.assertEqual(response.data['total'], 1)
        self.assertNotIn('SECRET-EXCUSE', str(response.data))

    def test_print_escaping_and_audit(self):
        self.attendance()
        response = self.client.post(reverse('api-report-print'), self.filters)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('SECRET-EXCUSE', html)
        self.assertIn('no-store', response['Cache-Control'])
        self.assertEqual(AuditLog.objects.get(action='REPORT_GENERATED').metadata['row_count'], 1)

    def test_invalid_filters(self):
        for values in ({'kind': 'wellbeing'}, {'page': 0}, {'student': 'bad'}, {'start': 'bad'}, {'end': str(self.today + timedelta(days=1))}, {'start': str(self.today + timedelta(days=1))}, {'start': str(self.today - timedelta(days=400))}):
            self.assertEqual(self.client.get(reverse('api-report-preview'), {**self.filters, **values}).status_code, 400)

    def test_pagination_and_complete_print(self):
        InterventionCase.objects.bulk_create([InterventionCase(student=self.student, reason='SECRET-REASON', findings='SECRET-FINDINGS', assigned_to=self.guidance, created_by=self.admin) for _ in range(51)])
        filters = {**self.filters, 'kind': 'interventions'}
        first = self.client.get(reverse('api-report-preview'), filters).data
        second = self.client.get(reverse('api-report-preview'), {**filters, 'page': 2}).data
        self.assertEqual(first['total'], 51)
        self.assertEqual(len(first['rows']), 50)
        self.assertEqual(len(second['rows']), 1)
        printed = self.client.post(reverse('api-report-print'), filters).content.decode()
        self.assertIn('51 records', printed)
        self.assertNotIn('SECRET-FINDINGS', printed)
        self.assertNotIn('SECRET-REASON', printed)

    def test_risk_confirmed_only(self):
        for offset, decision in enumerate(('PENDING', 'CONFIRMED', 'DISMISSED')):
            RiskAssessment.objects.create(student=self.student, assessed_on=self.today - timedelta(days=offset), period_start=self.today - timedelta(days=29), period_end=self.today - timedelta(days=offset), score=60, level='HIGH', review_decision=decision, reviewer_notes='SECRET-REVIEW', indicators={'private': 'SECRET-INDICATOR'})
        response = self.client.get(reverse('api-report-preview'), {**self.filters, 'kind': 'risk', 'start': str(self.today - timedelta(days=3))})
        self.assertEqual(response.data['total'], 1)
        self.assertNotIn('SECRET', str(response.data))

    def test_audit_sanitization_and_read_only(self):
        AuditLog.objects.bulk_create([AuditLog(actor=self.admin, action='PRIVATE_ACTION', object_type='Test', summary='SECRET-SUMMARY', metadata={'secret': 'SECRET-METADATA'}) for _ in range(51)])
        response = self.client.get(reverse('api-audit-logs'), {'action': 'PRIVATE_ACTION', 'actor': self.admin.pk, 'page': 2})
        self.assertEqual(response.data['total'], 51)
        self.assertEqual(len(response.data['rows']), 1)
        self.assertNotIn('SECRET', str(response.data))
        self.assertEqual(self.client.post(reverse('api-audit-logs'), {}).status_code, 405)

    def test_print_limit(self):
        with patch('reports.api.report_data') as data:
            data.return_value = (type('Records', (), {'count': lambda self: 5001})(), [], None)
            response = self.client.post(reverse('api-report-print'), self.filters)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AuditLog.objects.filter(action='REPORT_GENERATED').exists())
