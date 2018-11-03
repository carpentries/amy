from django.urls import reverse

from workshops.tests.base import TestBase
from workshops.lookups import urlpatterns


class TestLookups(TestBase):
    """Test suite for Django-Autocomplete-Light lookups."""

    def setUp(self):
        # prepare urlpatterns; only include lookup views that are restricted
        # to logged-in users and/or admins
        self.patterns_nonrestricted = ('language-lookup', )
        self.urlpatterns = filter(
            lambda pattern: pattern.name not in self.patterns_nonrestricted,
            urlpatterns
        )

    def test_login_regression(self):
        """Make sure lookups are login-protected"""
        for pattern in self.urlpatterns:
            rv = self.client.get(reverse(pattern.name))
            self.assertEqual(rv.status_code, 403, pattern.name)  # forbidden

        self._setUpUsersAndLogin()
        for pattern in self.urlpatterns:
            rv = self.client.get(reverse(pattern.name))
            self.assertEqual(rv.status_code, 200, pattern.name)  # OK
