from django.core.urlresolvers import reverse

from .base import TestBase


class TestLookups(TestBase):
    """Test suite for django-selectable lookups."""

    def test_login_regression(self):
        """Make sure lookups are login-protected"""
        url_name = 'selectable-lookup'
        rv = self.client.get(reverse(url_name, args=['workshops-hostlookup']))
        assert rv.status_code == 401  # unauthorized

        self._setUpUsersAndLogin()
        rv = self.client.get(reverse(url_name, args=['workshops-hostlookup']))
        assert rv.status_code == 200
