from django.core.exceptions import ValidationError

from ..models import NullableGitHubUsernameField
from .base import TestBase


class TestGitHubUsernameField(TestBase):
    def assertAccepts(self, value):
        field = NullableGitHubUsernameField()
        model_instance = None
        cleaned_value = field.clean(value, model_instance)
        self.assertEqual(cleaned_value, value)

    def assertRejects(self, value):
        field = NullableGitHubUsernameField()
        model_instance = None
        self.assertRaises(ValidationError, field.clean,
                          value, model_instance)

    def test_accepts_letters(self):
        self.assertAccepts('validname')

    def test_accepts_digits(self):
        self.assertAccepts('1234567')
        self.assertAccepts('1234asdff')

    def test_accepts_hyphens(self):
        self.assertAccepts('asdf-qwer')

    def test_rejects_underscores(self):
        self.assertRejects('under_score')

    def test_accepts_null(self):
        self.assertAccepts('')
        self.assertAccepts(None)
