from datetime import date, timedelta

from django.test import TestCase

from amy.extrequests.templatetags.request_membership import (
    membership_active,
    membership_alert_type,
)

from workshops.models import Membership


class TestMembershipAlertType(TestCase):
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

    def test_active_and_has_workshops(self):
        # Arrange
        expected = "info"

        # Act
        result = membership_alert_type(self.membership)

        # Assert
        self.assertEqual(expected, result)

    def test_active_and_no_workshops(self):
        # Arrange
        self.membership.workshops_without_admin_fee_per_agreement = 0
        expected = "warning"

        # Act
        result = membership_alert_type(self.membership)

        # Assert
        self.assertEqual(expected, result)

    def test_inactive_and_no_workshops(self):
        # Arrange
        self.membership.workshops_without_admin_fee_per_agreement = 0
        self.membership.agreement_end = date.today() - timedelta(days=1)
        expected = "warning"

        # Act
        result = membership_alert_type(self.membership)

        # Assert
        self.assertEqual(expected, result)

    def test_inactive_and_has_workshops(self):
        # Arrange
        self.membership.agreement_end = date.today() - timedelta(days=1)
        expected = "warning"

        # Act
        result = membership_alert_type(self.membership)

        # Assert
        self.assertEqual(expected, result)


class TestMembershipActive(TestCase):
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

    def test_active(self):
        # Arrange
        expected = True

        # Act
        result = membership_active(self.membership)

        # Assert
        self.assertEqual(expected, result)

    def test_inactive(self):
        # Arrange
        self.membership.agreement_end = date.today() - timedelta(days=1)
        expected = False

        # Act
        result = membership_active(self.membership)

        # Assert
        self.assertEqual(expected, result)
