from django.core.exceptions import ValidationError

from workshops.tests.base import TestBase
from workshops.fields import NullableGithubUsernameField


class TestNullableGHUsernameField(TestBase):
    def setUp(self):
        self.passing = [
            'harrypotter',
            'hp',
            'hpotter',
            'harry-potter',
            'harry-potter123',
            'Harry-Potter',
            '',
            None,
        ]

        self.failing = [
            'harry_potter',
            'harry--potter',
            '-harry',
            'potter-',
            'harry-averyveryverylongmiddlename-potter',
        ]

        self.field = NullableGithubUsernameField()

    def test_passing_usernames(self):
        """All correct usernames pass the field validation."""
        for username in self.passing:
            self.field.run_validators(username)

    def test_failing_usernames(self):
        """All incorrect usernames don't pass the field validation."""
        for username in self.failing:
            with self.assertRaises(ValidationError):
                self.field.run_validators(username)
