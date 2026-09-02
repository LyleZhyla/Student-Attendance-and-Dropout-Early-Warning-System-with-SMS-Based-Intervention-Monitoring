from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token

from audit_logs.models import AuditLog


class AccountPermissionTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(
            username='admin', email='admin@example.com', password='Admin-pass-4821', role=User.Role.ADMIN
        )
        self.teacher = User.objects.create_user(
            username='teacher', email='teacher@example.com', password='Teacher-pass-4821', role=User.Role.TEACHER
        )

    def auth(self, user):
        token = Token.objects.create(user=user)
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}

    def test_teacher_cannot_list_accounts(self):
        response = self.client.get(reverse('api-users'), **self.auth(self.teacher))
        self.assertEqual(response.status_code, 403)

    def test_superuser_is_aligned_to_administrator_role(self):
        superuser = get_user_model().objects.create_superuser(
            username='superadmin', password='Super-pass-4821', email='super@example.com'
        )
        self.assertEqual(superuser.role, 'ADMIN')
        self.assertTrue(superuser.is_staff)

    def test_admin_can_create_account_with_forced_password_change(self):
        response = self.client.post(
            reverse('api-users'),
            data={
                'username': 'student1', 'email': 'student1@example.com',
                'first_name': 'Student', 'last_name': 'One', 'role': 'STUDENT',
                'password': 'Student-temp-4821', 'password_confirm': 'Student-temp-4821',
            },
            content_type='application/json',
            **self.auth(self.admin),
        )
        self.assertEqual(response.status_code, 201)
        created = get_user_model().objects.get(username='student1')
        self.assertTrue(created.must_change_password)
        self.assertTrue(AuditLog.objects.filter(action='ACCOUNT_CREATED', object_id=str(created.pk)).exists())

    def test_admin_cannot_deactivate_self(self):
        response = self.client.post(
            reverse('api-user-status', args=[self.admin.pk]),
            data={'is_active': False}, content_type='application/json', **self.auth(self.admin),
        )
        self.assertEqual(response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_deactivation_revokes_existing_token(self):
        teacher_token = Token.objects.create(user=self.teacher)
        response = self.client.post(
            reverse('api-user-status', args=[self.teacher.pk]),
            data={'is_active': False}, content_type='application/json', **self.auth(self.admin),
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Token.objects.filter(key=teacher_token.key).exists())

    def test_last_active_admin_cannot_be_reassigned(self):
        response = self.client.patch(
            reverse('api-user-detail', args=[self.admin.pk]),
            data={'role': 'TEACHER'}, content_type='application/json', **self.auth(self.admin),
        )
        self.assertEqual(response.status_code, 400)


class PasswordManagementTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='student', password='Old-password-4821', role='STUDENT', must_change_password=True
        )
        self.token = Token.objects.create(user=self.user)

    def test_user_changes_password_and_token_is_rotated(self):
        response = self.client.post(
            reverse('api-change-password'),
            data={
                'current_password': 'Old-password-4821',
                'new_password': 'New-password-5932',
                'new_password_confirm': 'New-password-5932',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.token.key}',
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.must_change_password)
        self.assertTrue(self.user.check_password('New-password-5932'))
        self.assertNotEqual(response.json()['token'], self.token.key)

    def test_wrong_current_password_is_rejected(self):
        response = self.client.post(
            reverse('api-change-password'),
            data={
                'current_password': 'wrong',
                'new_password': 'New-password-5932',
                'new_password_confirm': 'New-password-5932',
            },
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Token {self.token.key}',
        )
        self.assertEqual(response.status_code, 400)

# Create your tests here.
