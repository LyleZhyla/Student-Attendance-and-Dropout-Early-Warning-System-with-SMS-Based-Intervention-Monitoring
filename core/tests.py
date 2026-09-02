from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


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

# Create your tests here.
