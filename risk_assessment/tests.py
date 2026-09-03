from datetime import time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token

from academics.models import ClassSchedule, GradeLevel, SchoolYear, Section, Subject
from attendance.models import AttendanceRecord
from audit_logs.models import AuditLog
from interventions.models import InterventionCase
from students.models import Enrollment, Student

from .models import RiskAssessment
from .services import ReviewedAssessmentExists, calculate_risk, generate_assessment


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class RiskAssessmentWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='risk-admin', password='Pass-4821', role=User.Role.ADMIN)
        self.guidance = User.objects.create_user(username='risk-guidance', password='Pass-4821', role=User.Role.GUIDANCE)
        self.teacher = User.objects.create_user(username='risk-teacher', password='Pass-4821', role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user(username='risk-other', password='Pass-4821', role=User.Role.TEACHER)
        self.parent = User.objects.create_user(username='risk-parent', password='Pass-4821', role=User.Role.PARENT)
        self.today = timezone.localdate()
        school_year = SchoolYear.objects.create(
            name='Risk test year', starts_on=self.today - timedelta(days=120), ends_on=self.today + timedelta(days=120), is_active=True
        )
        grade = GradeLevel.objects.create(name='Grade 10 Risk', order=10)
        section = Section.objects.create(name='Luna', grade_level=grade, school_year=school_year, adviser=self.teacher)
        subject = Subject.objects.create(code='RISK10', name='Risk Test Subject')
        self.schedule = ClassSchedule.objects.create(
            section=section, subject=subject, teacher=self.teacher, weekday=1,
            starts_at=time(8), ends_at=time(9),
        )
        self.student = Student.objects.create(
            learner_reference_number='500000000001', first_name='Rina', last_name='Santos'
        )
        self.outsider = Student.objects.create(
            learner_reference_number='500000000002', first_name='Luis', last_name='Reyes'
        )
        Enrollment.objects.create(
            student=self.student, section=section, status=Enrollment.Status.ENROLLED,
            enrolled_on=self.today - timedelta(days=90),
        )

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def attendance(self, offset, status):
        return AttendanceRecord.objects.create(
            student=self.student, class_schedule=self.schedule, date=self.today + timedelta(days=offset),
            status=status, encoded_by=self.teacher,
        )

    def seed_high_risk_inputs(self):
        for offset in (-2, -1, 0):
            self.attendance(offset, AttendanceRecord.Status.ABSENT_UNEXCUSED)
        self.attendance(-3, AttendanceRecord.Status.LATE)
        self.attendance(-4, AttendanceRecord.Status.LATE)
        for offset in (-35, -36, -37, -38, -39):
            self.attendance(offset, AttendanceRecord.Status.PRESENT)
        InterventionCase.objects.create(
            student=self.student, reason='Existing unresolved support case.',
            assigned_to=self.guidance, created_by=self.admin,
        )

    def test_calculation_is_explainable_and_uses_documented_bands(self):
        self.seed_high_risk_inputs()
        result = calculate_risk(self.student, self.today)
        self.assertEqual(result['score'], 65)
        self.assertEqual(result['level'], RiskAssessment.Level.HIGH)
        components = {item['key']: item for item in result['indicators']['components']}
        self.assertEqual(components['unexcused_absences']['points'], 24)
        self.assertEqual(components['consecutive_unexcused_days']['points'], 10)
        self.assertEqual(components['late_records']['points'], 6)
        self.assertEqual(components['attendance_decline']['points'], 15)
        self.assertEqual(components['open_interventions']['points'], 10)
        self.assertIn('not a diagnosis', result['indicators']['disclaimer'])

    def test_pending_generation_is_idempotent_but_reviewed_result_is_immutable(self):
        assessment, created = generate_assessment(self.student, self.today, self.admin)
        self.assertTrue(created)
        recalculated, created = generate_assessment(self.student, self.today, self.guidance)
        self.assertFalse(created)
        self.assertEqual(recalculated.pk, assessment.pk)
        recalculated.review_decision = RiskAssessment.ReviewDecision.CONFIRMED
        recalculated.reviewed_by = self.guidance
        recalculated.reviewed_at = timezone.now()
        recalculated.save()
        with self.assertRaises(ReviewedAssessmentExists):
            generate_assessment(self.student, self.today, self.admin)

    def test_model_rejects_level_that_does_not_match_score(self):
        assessment = RiskAssessment(
            student=self.student, score=75, level=RiskAssessment.Level.LOW,
            indicators={}, period_start=self.today - timedelta(days=29), period_end=self.today,
            assessed_on=self.today,
        )
        with self.assertRaises(ValidationError):
            assessment.full_clean()

    def test_admin_and_guidance_can_generate_but_teacher_and_parent_cannot(self):
        endpoint = reverse('api-risk-generate')
        teacher = self.client.post(endpoint, {'student': self.student.pk}, content_type='application/json', **self.auth(self.teacher))
        parent = self.client.post(endpoint, {'student': self.student.pk}, content_type='application/json', **self.auth(self.parent))
        admin = self.client.post(endpoint, {'student': self.student.pk}, content_type='application/json', **self.auth(self.admin))
        self.assertEqual(teacher.status_code, 403)
        self.assertEqual(parent.status_code, 403)
        self.assertEqual(admin.status_code, 201)
        self.assertTrue(AuditLog.objects.filter(action='RISK_ASSESSMENT_GENERATED').exists())

    def test_future_generation_is_rejected(self):
        response = self.client.post(reverse('api-risk-generate'), {
            'student': self.student.pk, 'assessed_on': self.today + timedelta(days=1)
        }, content_type='application/json', **self.auth(self.guidance))
        self.assertEqual(response.status_code, 400)

    def test_teacher_only_sees_confirmed_results_for_assigned_students(self):
        assessment, _ = generate_assessment(self.student, self.today, self.admin)
        pending = self.client.get(reverse('api-risk-assessments'), **self.auth(self.teacher))
        self.assertEqual(pending.json()['records'], [])
        assessment.review_decision = RiskAssessment.ReviewDecision.CONFIRMED
        assessment.reviewed_by = self.guidance
        assessment.reviewed_at = timezone.now()
        assessment.reviewer_notes = 'Internal validation note.'
        assessment.save()
        confirmed = self.client.get(reverse('api-risk-assessments'), **self.auth(self.teacher))
        other = self.client.get(reverse('api-risk-assessments'), **self.auth(self.other_teacher))
        self.assertEqual([item['id'] for item in confirmed.json()['records']], [assessment.pk])
        self.assertEqual(confirmed.json()['records'][0]['reviewer_notes'], '')
        self.assertEqual(other.json()['records'], [])

    def test_review_requires_authorized_reviewer_and_notes_for_nonconfirmation(self):
        assessment, _ = generate_assessment(self.student, self.today, self.admin)
        endpoint = reverse('api-risk-review', args=[assessment.pk])
        denied = self.client.post(endpoint, {'decision': 'CONFIRMED'}, content_type='application/json', **self.auth(self.teacher))
        missing_notes = self.client.post(endpoint, {'decision': 'DISMISSED'}, content_type='application/json', **self.auth(self.guidance))
        reviewed = self.client.post(endpoint, {
            'decision': 'NEEDS_MORE_INFO', 'notes': 'Verify the attendance correction with the adviser.'
        }, content_type='application/json', **self.auth(self.guidance))
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(missing_notes.status_code, 400)
        self.assertEqual(reviewed.status_code, 200)
        assessment.refresh_from_db()
        self.assertEqual(assessment.review_decision, RiskAssessment.ReviewDecision.NEEDS_MORE_INFO)
        self.assertEqual(assessment.reviewed_by, self.guidance)
        self.assertTrue(AuditLog.objects.filter(action='RISK_ASSESSMENT_REVIEWED').exists())

# Create your tests here.
