import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.authtoken.models import Token
from students.models import Student


class DashboardTests(TestCase):
    def test_root_and_client_routes_serve_the_react_app(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            Path(temp_dir, 'index.html').write_text('<div id="root">TardyTrack</div>', encoding='utf-8')
            with override_settings(REACT_BUILD_DIR=Path(temp_dir)):
                self.assertContains(self.client.get('/'), 'TardyTrack')
                self.assertContains(self.client.get('/dashboard'), 'TardyTrack')

    def test_missing_react_build_has_helpful_response(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with override_settings(REACT_BUILD_DIR=Path(temp_dir)):
                response = self.client.get('/')
        self.assertEqual(response.status_code, 503)
        self.assertContains(response, 'run-system.cmd', status_code=503)


class ApiAuthenticationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='admin', email='admin@example.com', password='safe-test-password',
            first_name='Tardy', last_name='Admin', role='ADMIN'
        )

    def test_login_accepts_email_and_returns_role(self):
        response = self.client.post(
            reverse('api-login'),
            data={'identifier': 'admin@example.com', 'password': 'safe-test-password'},
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['user']['role'], 'ADMIN')
        self.assertIn('must_change_password', response.json()['user'])
        self.assertTrue(Token.objects.filter(user=self.user).exists())

    def test_dashboard_api_requires_token(self):
        response = self.client.get(reverse('api-dashboard-summary'))
        self.assertEqual(response.status_code, 401)

    def test_dashboard_api_returns_tardytrack_metrics(self):
        token = Token.objects.create(user=self.user)
        response = self.client.get(
            reverse('api-dashboard-summary'), HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('active_students', response.json()['metrics'])
        self.assertIn('month_attendance_rate', response.json()['metrics'])
        self.assertEqual(len(response.json()['attendance_overview']['seven_day_trend']), 7)
        self.assertTrue(response.json()['capabilities']['manage_users'])

    def test_teacher_dashboard_does_not_expose_unassigned_students(self):
        teacher = get_user_model().objects.create_user(
            username='teacher-scope', password='safe-test-password', role='TEACHER'
        )
        Student.objects.create(
            learner_reference_number='999999999999', first_name='Not', last_name='Assigned'
        )
        token = Token.objects.create(user=teacher)
        response = self.client.get(
            reverse('api-dashboard-summary'), HTTP_AUTHORIZATION=f'Token {token.key}'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['metrics']['active_students'], 0)
        self.assertFalse(response.json()['capabilities']['manage_users'])

# Create your tests here.
