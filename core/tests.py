from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from students.models import Student


class DashboardTests(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_authenticated_user_sees_role_dashboard(self):
        user = get_user_model().objects.create_user(
            username='teacher', password='safe-test-password', role='TEACHER'
        )
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Teacher workspace')
        self.assertContains(response, 'Foundation ready')


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
