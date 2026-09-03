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

from .models import RiskAssessment, WellBeingCheckIn
from .services import ReviewedAssessmentExists, calculate_risk, generate_assessment
from .well_being import PRIVACY_NOTICE_VERSION


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


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class WellBeingCheckInTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='well-admin', password='Pass-4821', role=User.Role.ADMIN)
        self.guidance = User.objects.create_user(username='well-guidance', password='Pass-4821', role=User.Role.GUIDANCE)
        self.teacher = User.objects.create_user(username='well-teacher', password='Pass-4821', role=User.Role.TEACHER)
        self.parent = User.objects.create_user(username='well-parent', password='Pass-4821', role=User.Role.PARENT)
        self.student_user = User.objects.create_user(username='well-student', password='Pass-4821', role=User.Role.STUDENT)
        self.today = timezone.localdate()
        self.student = Student.objects.create(
            user=self.student_user, learner_reference_number='500000000099', first_name='Mia', last_name='Garcia'
        )

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def payload(self, **overrides):
        values = {
            'student': self.student.pk,
            'conducted_on': str(self.today),
            'privacy_notice_version': PRIVACY_NOTICE_VERSION,
            'consent_confirmed': True,
            'responses': {
                'attendance_barriers': 'SOME',
                'school_connection': 'OKAY',
                'support_access': 'YES',
                'support_requested': True,
                'support_topics': ['ACADEMIC', 'TRANSPORTATION'],
            },
            'support_priority': 'PROMPT',
            'private_notes': 'Restricted guidance context.',
            'recommended_actions': '',
        }
        values.update(overrides)
        return values

    def create(self, **overrides):
        return self.client.post(
            reverse('api-well-being-checkins'), self.payload(**overrides),
            content_type='application/json', **self.auth(self.guidance),
        )

    def test_only_admin_and_guidance_can_access_restricted_records(self):
        self.assertEqual(self.client.get(reverse('api-well-being-checkins'), **self.auth(self.admin)).status_code, 200)
        self.assertEqual(self.client.get(reverse('api-well-being-checkins'), **self.auth(self.guidance)).status_code, 200)
        self.assertEqual(self.client.get(reverse('api-well-being-checkins'), **self.auth(self.teacher)).status_code, 403)
        self.assertEqual(self.client.get(reverse('api-well-being-checkins'), **self.auth(self.parent)).status_code, 403)
        self.assertEqual(self.client.get(reverse('api-well-being-checkins'), **self.auth(self.student_user)).status_code, 403)

    def test_create_requires_consent_current_notice_and_approved_response_schema(self):
        self.assertEqual(self.create(consent_confirmed=False).status_code, 400)
        self.assertEqual(self.create(privacy_notice_version='old-notice').status_code, 400)
        invalid = self.payload()
        invalid['responses']['unsupported_question'] = 'value'
        response = self.client.post(
            reverse('api-well-being-checkins'), invalid, content_type='application/json', **self.auth(self.guidance)
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(WellBeingCheckIn.objects.exists())

    def test_collection_excludes_raw_responses_and_private_notes(self):
        created = self.create()
        self.assertEqual(created.status_code, 201)
        record_id = created.json()['record']['id']
        listing = self.client.get(reverse('api-well-being-checkins'), **self.auth(self.admin)).json()['records'][0]
        detail = self.client.get(reverse('api-well-being-detail', args=[record_id]), **self.auth(self.admin)).json()['record']
        self.assertNotIn('responses', listing)
        self.assertNotIn('private_notes', listing)
        self.assertEqual(detail['responses']['support_requested'], True)
        self.assertEqual(detail['private_notes'], 'Restricted guidance context.')

    def test_duplicate_student_date_is_rejected_as_conflict(self):
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.create().status_code, 409)

    def test_submitted_responses_and_identity_are_immutable(self):
        record_id = self.create().json()['record']['id']
        response = self.client.patch(
            reverse('api-well-being-detail', args=[record_id]), {'responses': self.payload()['responses']},
            content_type='application/json', **self.auth(self.admin),
        )
        self.assertEqual(response.status_code, 400)

    def test_action_plan_and_closure_rules_are_enforced(self):
        record_id = self.create(private_notes='').json()['record']['id']
        endpoint = reverse('api-well-being-detail', args=[record_id])
        missing_plan = self.client.patch(
            endpoint, {'status': 'ACTION_PLANNED'}, content_type='application/json', **self.auth(self.guidance)
        )
        self.assertEqual(missing_plan.status_code, 400)
        planned = self.client.patch(endpoint, {
            'status': 'ACTION_PLANNED', 'support_priority': 'URGENT',
            'recommended_actions': 'Guidance will meet the student today and coordinate approved support.'
        }, content_type='application/json', **self.auth(self.guidance))
        self.assertEqual(planned.status_code, 200)
        closed_missing_notes = self.client.patch(
            endpoint, {'status': 'CLOSED'}, content_type='application/json', **self.auth(self.guidance)
        )
        self.assertEqual(closed_missing_notes.status_code, 400)
        closed = self.client.patch(endpoint, {
            'status': 'CLOSED', 'private_notes': 'Approved support handoff completed.'
        }, content_type='application/json', **self.auth(self.guidance))
        self.assertEqual(closed.status_code, 200)
        self.assertEqual(closed.json()['record']['status'], 'CLOSED')
        immutable = self.client.patch(
            endpoint, {'private_notes': 'Changed'}, content_type='application/json', **self.auth(self.admin)
        )
        self.assertEqual(immutable.status_code, 400)

    def test_audit_log_does_not_copy_responses_or_private_notes(self):
        self.create()
        event = AuditLog.objects.get(action='WELL_BEING_CHECKIN_CREATED')
        serialized = str(event.metadata)
        self.assertNotIn('attendance_barriers', serialized)
        self.assertNotIn('Restricted guidance context', serialized)

    def test_well_being_responses_do_not_change_automated_risk_score(self):
        before = calculate_risk(self.student, self.today)['score']
        self.assertEqual(self.create().status_code, 201)
        after = calculate_risk(self.student, self.today)['score']
        self.assertEqual(before, after)

# Create your tests here.
