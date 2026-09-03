from datetime import date
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token

from audit_logs.models import AuditLog
from attendance.models import AttendanceRecord
from students.models import Guardian, Student, StudentGuardian

from .models import SMSLog
from .services import queue_attendance_notifications, queue_sms, send_sms


class SuccessfulProvider:
    def send(self, recipient, message):
        return {'reference': 'provider-123', 'delivered': True}


class FailingProvider:
    def send(self, recipient, message):
        raise RuntimeError('Temporary provider failure')


class SMSNotificationTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='sms-admin', password='Pass-4821', role=User.Role.ADMIN)
        self.teacher = User.objects.create_user(username='sms-teacher', password='Pass-4821', role=User.Role.TEACHER)
        self.student = Student.objects.create(
            learner_reference_number='300000000001', first_name='Lina', last_name='Cruz'
        )
        self.guardian = Guardian.objects.create(
            full_name='Rosa Cruz', relationship='Mother', mobile_number='09171234567',
            sms_consent=True, mobile_verified=True,
        )
        StudentGuardian.objects.create(student=self.student, guardian=self.guardian, is_primary=True)

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def payload(self, **overrides):
        values = {
            'student': self.student.pk, 'guardian': self.guardian.pk, 'category': 'ATTENDANCE',
            'message': 'Attendance notice for Lina.', 'event_key': 'attendance:test:1',
        }
        values.update(overrides)
        return values

    def test_queue_requires_link_consent_and_verified_mobile(self):
        self.guardian.sms_consent = False
        self.guardian.save(update_fields=('sms_consent',))
        with self.assertRaises(ValidationError):
            queue_sms(
                student=self.student, guardian=self.guardian, category='GENERAL', message='Test',
                event_key='manual:test:1', created_by=self.admin,
            )
        self.guardian.sms_consent = True
        self.guardian.mobile_verified = False
        self.guardian.save(update_fields=('sms_consent', 'mobile_verified'))
        with self.assertRaises(ValidationError):
            queue_sms(
                student=self.student, guardian=self.guardian, category='GENERAL', message='Test',
                event_key='manual:test:2', created_by=self.admin,
            )

    def test_event_key_prevents_duplicate_notifications(self):
        queue_sms(
            student=self.student, guardian=self.guardian, category='GENERAL', message='First',
            event_key='manual:duplicate', created_by=self.admin,
        )
        with self.assertRaises(ValidationError):
            queue_sms(
                student=self.student, guardian=self.guardian, category='GENERAL', message='Second',
                event_key='manual:duplicate', created_by=self.admin,
            )

    def test_provider_success_tracks_delivery_without_exposing_number(self):
        log = queue_sms(
            student=self.student, guardian=self.guardian, category='GENERAL', message='Test',
            event_key='manual:delivery', created_by=self.admin,
        )
        sent = send_sms(log.pk, provider=SuccessfulProvider())
        self.assertEqual(sent.status, SMSLog.Status.DELIVERED)
        self.assertEqual(sent.provider_reference, 'provider-123')
        self.assertIsNotNone(sent.sent_at)
        self.assertIsNotNone(sent.delivered_at)
        self.assertNotIn('1234567', sent.recipient_masked)

    def test_send_cancels_when_consent_is_withdrawn(self):
        log = queue_sms(
            student=self.student, guardian=self.guardian, category='GENERAL', message='Test',
            event_key='manual:withdrawn', created_by=self.admin,
        )
        self.guardian.sms_consent = False
        self.guardian.save(update_fields=('sms_consent',))
        result = send_sms(log.pk, provider=SuccessfulProvider())
        self.assertEqual(result.status, SMSLog.Status.CANCELLED)
        self.assertIsNone(result.sent_at)

    @override_settings(SMS_AUTO_ATTENDANCE_NOTIFICATIONS=True)
    def test_automated_attendance_alert_is_idempotent_and_cancelled_after_correction(self):
        record = SimpleNamespace(
            pk=77, student=self.student, date=date(2026, 9, 3),
            Status=AttendanceRecord.Status, status=AttendanceRecord.Status.ABSENT_UNEXCUSED,
        )
        self.assertEqual(len(queue_attendance_notifications(record, self.admin)), 1)
        self.assertEqual(len(queue_attendance_notifications(record, self.admin)), 0)
        self.assertEqual(SMSLog.objects.count(), 1)
        record.status = AttendanceRecord.Status.PRESENT
        self.assertEqual(queue_attendance_notifications(record, self.admin), [])
        self.assertEqual(SMSLog.objects.get().status, SMSLog.Status.CANCELLED)

    @override_settings(SMS_MAX_RETRIES=1)
    def test_provider_failure_is_retained_and_retry_limit_is_enforced(self):
        log = queue_sms(
            student=self.student, guardian=self.guardian, category='GENERAL', message='Test',
            event_key='manual:failure', created_by=self.admin,
        )
        failed = send_sms(log.pk, provider=FailingProvider())
        self.assertEqual(failed.status, SMSLog.Status.FAILED)
        self.assertEqual(failed.retry_count, 1)
        self.assertIn('Temporary provider failure', failed.error_message)
        unchanged = send_sms(log.pk, provider=SuccessfulProvider())
        self.assertEqual(unchanged.status, SMSLog.Status.FAILED)

    def test_admin_can_queue_and_send_but_teacher_cannot(self):
        denied = self.client.post(
            reverse('api-sms-logs'), self.payload(), content_type='application/json', **self.auth(self.teacher)
        )
        self.assertEqual(denied.status_code, 403)
        created = self.client.post(
            reverse('api-sms-logs'), self.payload(), content_type='application/json', **self.auth(self.admin)
        )
        self.assertEqual(created.status_code, 201)
        record_id = created.json()['record']['id']
        sent = self.client.post(reverse('api-sms-send', args=[record_id]), {}, content_type='application/json', **self.auth(self.admin))
        self.assertEqual(sent.status_code, 200)
        self.assertEqual(sent.json()['record']['status'], SMSLog.Status.SENT)
        self.assertTrue(AuditLog.objects.filter(action='SMS_QUEUED').exists())
        self.assertTrue(AuditLog.objects.filter(action='SMS_SENT').exists())

    def test_duplicate_api_request_returns_conflict(self):
        auth = self.auth(self.admin)
        self.assertEqual(self.client.post(reverse('api-sms-logs'), self.payload(), content_type='application/json', **auth).status_code, 201)
        duplicate = self.client.post(reverse('api-sms-logs'), self.payload(), content_type='application/json', **auth)
        self.assertEqual(duplicate.status_code, 409)

    def test_options_explain_ineligible_recipients(self):
        self.guardian.mobile_verified = False
        self.guardian.save(update_fields=('mobile_verified',))
        response = self.client.get(reverse('api-sms-options'), **self.auth(self.admin))
        recipient = response.json()['recipients'][0]
        self.assertFalse(recipient['eligible'])
        self.assertIn('not verified', recipient['ineligible_reason'])

# Create your tests here.
