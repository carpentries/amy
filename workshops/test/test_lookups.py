from django.urls import reverse

from .base import TestBase
from ..lookups import urlpatterns


class TestLookups(TestBase):
    """Test suite for django-selectable lookups."""

    def test_login_regression(self):
        """Make sure lookups are login-protected"""
        for pattern in urlpatterns:
            rv = self.client.get(reverse(pattern.name))
            self.assertEqual(rv.status_code, 403, pattern.name)  # forbidden

        self._setUpUsersAndLogin()
        for pattern in urlpatterns:
            rv = self.client.get(reverse(pattern.name))
            self.assertEqual(rv.status_code, 200, pattern.name)  # OK
