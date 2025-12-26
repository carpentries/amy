from django.test import TestCase

from src.emails.models import ScheduledEmailStatus
from src.emails.templatetags.emails import allowed_actions_for_status


class TestAllowedActionsForStatusTag(TestCase):
    def test_allowed_actions_for_status__empty(self) -> None:
        # Arrange
        statuses = [
            ScheduledEmailStatus.LOCKED,
            ScheduledEmailStatus.RUNNING,
        ]
        # Act & Assert
        for status in statuses:
            result = allowed_actions_for_status(status)
            self.assertEqual(result, [])

    def test_allowed_actions_for_status__all_actions(self) -> None:
        # Arrange
        statuses = [
            ScheduledEmailStatus.SCHEDULED,
            ScheduledEmailStatus.FAILED,
        ]
        # Act & Assert
        for status in statuses:
            result = allowed_actions_for_status(status)
            self.assertEqual(result, ["edit", "reschedule", "cancel"])

    def test_allowed_actions_for_status__specific_actions(self) -> None:
        # Act
        result1 = allowed_actions_for_status(ScheduledEmailStatus.SUCCEEDED)
        result2 = allowed_actions_for_status(ScheduledEmailStatus.CANCELLED)
        # Assert
        self.assertEqual(result1, [])
        self.assertEqual(result2, ["edit", "reschedule"])
