from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token

from academics.models import ClassSchedule, GradeLevel, SchoolYear, Section, Subject
from audit_logs.models import AuditLog
from students.models import Enrollment, Guardian, Student, StudentGuardian

from .models import InterventionActivity, InterventionCase


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class InterventionWorkflowTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='case-admin', password='Pass-4821', role=User.Role.ADMIN)
        self.guidance = User.objects.create_user(username='guidance', password='Pass-4821', role=User.Role.GUIDANCE)
        self.teacher = User.objects.create_user(username='case-teacher', password='Pass-4821', role=User.Role.TEACHER)
        self.other_teacher = User.objects.create_user(username='case-other', password='Pass-4821', role=User.Role.TEACHER)
        self.parent = User.objects.create_user(username='case-parent', password='Pass-4821', role=User.Role.PARENT)
        today = timezone.localdate()
        school_year = SchoolYear.objects.create(
            name='Case test year', starts_on=today - timedelta(days=60), ends_on=today + timedelta(days=180), is_active=True
        )
        grade = GradeLevel.objects.create(name='Grade 9 Case', order=9)
        self.section = Section.objects.create(
            name='Bonifacio', grade_level=grade, school_year=school_year, adviser=self.teacher
        )
        subject = Subject.objects.create(code='CASE9', name='Case Subject')
        ClassSchedule.objects.create(
            section=self.section, subject=subject, teacher=self.teacher, weekday=1,
            starts_at='08:00', ends_at='09:00',
        )
        self.student = Student.objects.create(
            learner_reference_number='400000000001', first_name='Nina', last_name='Lopez'
        )
        self.outsider = Student.objects.create(
            learner_reference_number='400000000002', first_name='Omar', last_name='Diaz'
        )
        Enrollment.objects.create(
            student=self.student, section=self.section, status=Enrollment.Status.ENROLLED,
            enrolled_on=today - timedelta(days=30),
        )
        self.guardian = Guardian.objects.create(
            full_name='Elena Lopez', relationship='Mother', mobile_number='09175550123'
        )
        self.other_guardian = Guardian.objects.create(
            full_name='Other Guardian', relationship='Aunt', mobile_number='09175550456'
        )
        StudentGuardian.objects.create(student=self.student, guardian=self.guardian, is_primary=True)

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def payload(self, **overrides):
        values = {
            'student': self.student.pk, 'reason': 'Repeated attendance concerns requiring support.',
            'assigned_to': self.guidance.pk, 'status': InterventionCase.Status.FOR_REVIEW,
        }
        values.update(overrides)
        return values

    def create_case(self, assigned_to=None, status=InterventionCase.Status.FOR_REVIEW, **extra):
        return InterventionCase.objects.create(
            student=self.student, reason='Support is needed.', status=status,
            assigned_to=assigned_to or self.guidance, created_by=self.admin, **extra,
        )

    def test_model_requires_schedule_follow_up_and_resolution_findings(self):
        scheduled = self.create_case(status=InterventionCase.Status.MEETING_SCHEDULED)
        with self.assertRaises(ValidationError):
            scheduled.full_clean()
        follow_up = self.create_case(status=InterventionCase.Status.FOR_FOLLOW_UP)
        with self.assertRaises(ValidationError):
            follow_up.full_clean()
        resolved = self.create_case(status=InterventionCase.Status.RESOLVED)
        with self.assertRaises(ValidationError):
            resolved.full_clean()

    def test_admin_creates_case_with_audit_and_status_activity(self):
        response = self.client.post(
            reverse('api-intervention-cases'), self.payload(), content_type='application/json', **self.auth(self.admin)
        )
        self.assertEqual(response.status_code, 201)
        case = InterventionCase.objects.get()
        self.assertEqual(case.created_by, self.admin)
        self.assertEqual(case.status, InterventionCase.Status.FOR_REVIEW)
        self.assertTrue(case.activities.filter(activity_type=InterventionActivity.Type.STATUS_CHANGE).exists())
        self.assertTrue(AuditLog.objects.filter(action='INTERVENTION_CREATED').exists())

    def test_teacher_scope_and_forced_case_ownership(self):
        response = self.client.post(
            reverse('api-intervention-cases'), self.payload(assigned_to=self.guidance.pk),
            content_type='application/json', **self.auth(self.teacher),
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(InterventionCase.objects.get().assigned_to, self.teacher)
        denied = self.client.post(
            reverse('api-intervention-cases'), self.payload(student=self.outsider.pk),
            content_type='application/json', **self.auth(self.teacher),
        )
        self.assertEqual(denied.status_code, 404)

    def test_parent_is_denied_and_other_teacher_cannot_see_case(self):
        case = self.create_case()
        parent_response = self.client.get(reverse('api-intervention-cases'), **self.auth(self.parent))
        other_response = self.client.get(reverse('api-intervention-case-detail', args=[case.pk]), **self.auth(self.other_teacher))
        self.assertEqual(parent_response.status_code, 403)
        self.assertEqual(other_response.status_code, 404)

    def test_teacher_can_view_assigned_student_case_but_only_owner_can_change_it(self):
        case = self.create_case(assigned_to=self.guidance)
        listing = self.client.get(reverse('api-intervention-cases'), **self.auth(self.teacher))
        self.assertEqual([item['id'] for item in listing.json()['records']], [case.pk])
        denied = self.client.patch(
            reverse('api-intervention-case-detail', args=[case.pk]), {'reason': 'Changed'},
            content_type='application/json', **self.auth(self.teacher),
        )
        self.assertEqual(denied.status_code, 403)

    def test_status_transitions_are_enforced_and_recorded(self):
        case = self.create_case()
        invalid = self.client.patch(
            reverse('api-intervention-case-detail', args=[case.pk]), {'status': InterventionCase.Status.RESOLVED, 'findings': 'Done'},
            content_type='application/json', **self.auth(self.guidance),
        )
        self.assertEqual(invalid.status_code, 400)
        valid = self.client.patch(
            reverse('api-intervention-case-detail', args=[case.pk]), {'status': InterventionCase.Status.CONTACTING_PARENT},
            content_type='application/json', **self.auth(self.guidance),
        )
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(valid.json()['record']['status'], InterventionCase.Status.CONTACTING_PARENT)
        self.assertEqual(case.activities.filter(activity_type=InterventionActivity.Type.STATUS_CHANGE).count(), 1)

    def test_case_student_cannot_be_changed(self):
        case = self.create_case()
        response = self.client.patch(
            reverse('api-intervention-case-detail', args=[case.pk]), {'student': self.outsider.pk},
            content_type='application/json', **self.auth(self.guidance),
        )
        self.assertEqual(response.status_code, 400)
        case.refresh_from_db()
        self.assertEqual(case.student, self.student)

    def test_scheduled_transition_requires_future_datetime(self):
        case = self.create_case(status=InterventionCase.Status.CONTACTING_PARENT)
        missing = self.client.patch(
            reverse('api-intervention-case-detail', args=[case.pk]), {'status': InterventionCase.Status.MEETING_SCHEDULED},
            content_type='application/json', **self.auth(self.guidance),
        )
        self.assertEqual(missing.status_code, 400)
        valid = self.client.patch(
            reverse('api-intervention-case-detail', args=[case.pk]), {
                'status': InterventionCase.Status.MEETING_SCHEDULED,
                'scheduled_for': (timezone.now() + timedelta(days=2)).isoformat(),
            }, content_type='application/json', **self.auth(self.guidance),
        )
        self.assertEqual(valid.status_code, 200)

    def test_parent_contact_activity_requires_linked_guardian_and_outcome(self):
        case = self.create_case()
        endpoint = reverse('api-intervention-activities', args=[case.pk])
        missing = self.client.post(
            endpoint, {'activity_type': 'PARENT_CONTACT', 'notes': 'Called home.'},
            content_type='application/json', **self.auth(self.guidance),
        )
        self.assertEqual(missing.status_code, 400)
        unlinked = self.client.post(endpoint, {
            'activity_type': 'PARENT_CONTACT', 'guardian': self.other_guardian.pk,
            'channel': 'PHONE', 'outcome': 'NO_ANSWER', 'notes': 'No answer.'
        }, content_type='application/json', **self.auth(self.guidance))
        self.assertEqual(unlinked.status_code, 400)
        created = self.client.post(endpoint, {
            'activity_type': 'PARENT_CONTACT', 'guardian': self.guardian.pk,
            'channel': 'PHONE', 'outcome': 'REACHED', 'notes': 'Guardian agreed to a school meeting.'
        }, content_type='application/json', **self.auth(self.guidance))
        self.assertEqual(created.status_code, 201)
        self.assertTrue(AuditLog.objects.filter(action='INTERVENTION_ACTIVITY_ADDED').exists())

# Create your tests here.
