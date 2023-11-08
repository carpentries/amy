from datetime import date, timedelta

from django.test import TestCase

from amy.extrequests.templatetags.request_membership import membership_description
from workshops.models import Membership


class TestMembershipDescription(TestCase):
    def setUp(self):
        self.membership = Membership.objects.create(
            name="Alpha Organization",
            variant="bronze",
            agreement_start=date.today() - timedelta(weeks=26),
            agreement_end=date.today() + timedelta(weeks=26),
            contribution_type="financial",
            registration_code="valid123",
            workshops_without_admin_fee_per_agreement=2,
        )

    def test_not_a_membership(self):
        # Arrange
        expected = ""

        # Act
        result = membership_description("some-string")

        # Assert
        self.assertEqual(expected, result)

    def test_active_and_has_workshops(self):
        # Arrange
        expected = (
            '<div class="alert alert-info">Related membership:'
            f'<a href="{self.membership.get_absolute_url()}">{self.membership}</a>.<br>'
            "This membership has <strong>2</strong> workshops remaining.</div>"
        )

        # Act
        result = membership_description(self.membership)

        # Assert
        self.assertHTMLEqual(expected, result)

    def test_active_and_no_workshops(self):
        # Arrange
        self.membership.workshops_without_admin_fee_per_agreement = 0
        expected = (
            '<div class="alert alert-warning">Related membership:'
            f'<a href="{self.membership.get_absolute_url()}">{self.membership}</a>.<br>'
            "This membership has <strong>0</strong> workshops remaining.</div>"
        )

        # Act
        result = membership_description(self.membership)

        # Assert
        self.assertHTMLEqual(expected, result)

    def test_inactive_and_no_workshops(self):
        # Arrange
        self.membership.workshops_without_admin_fee_per_agreement = 0
        self.membership.agreement_end = date.today() - timedelta(days=1)
        expected = (
            '<div class="alert alert-warning">Related membership:'
            f'<a href="{self.membership.get_absolute_url()}">{self.membership}</a>.<br>'
            "This membership has <strong>0</strong> workshops remaining."
            "<br>This membership is <strong>not currently active</strong>."
            "</div>"
        )

        # Act
        result = membership_description(self.membership)

        # Assert
        self.assertHTMLEqual(expected, result)

    def test_inactive_and_has_workshops(self):
        # Arrange
        self.membership.agreement_end = date.today() - timedelta(days=1)
        expected = (
            '<div class="alert alert-warning">Related membership:'
            f'<a href="{self.membership.get_absolute_url()}">{self.membership}</a>.<br>'
            "This membership has <strong>2</strong> workshops remaining."
            "<br>This membership is <strong>not currently active</strong>."
            "</div>"
        )

        # Act
        result = membership_description(self.membership)

        # Assert
        self.assertHTMLEqual(expected, result)
