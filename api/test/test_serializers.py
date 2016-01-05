from django.test import TestCase

from ..serializers import PersonUsernameSerializer
from workshops.models import Person


class TestPersonUsernameSerializer(TestCase):
    def setUp(self):
        self.user1 = Person.objects.create_user(username='test.user',
                                                personal='User', family='Test',
                                                email='test@user.com')

    def test_username(self):
        """Ensure we change dots to underscores."""
        serialized = PersonUsernameSerializer(self.user1)
        self.assertEqual(serialized.data['user'], 'test_user')
