from django.core.urlresolvers import reverse

from workshops.models import Person
from workshops.test import TestBase


class TestTraineeDashboard(TestBase):
    """Tests for trainee dashboard."""
    def setUp(self):
        self.user = Person.objects.create_user(
            username='user', personal='', family='',
            email='user@example.org', password='pass')
        self.client.login(username='user', password='pass')

    def test_dashboard_loads(self):
        rv = self.client.get(reverse('trainee-dashboard'))
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self.assertIn("Log out", content)
        self.assertIn("Update your profile", content)
