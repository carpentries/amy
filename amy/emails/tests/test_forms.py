from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from emails.forms import ScheduledEmailRescheduleForm


class TestScheduledEmailRescheduleForm(TestCase):
    @patch("emails.forms.datetime", wraps=datetime)
    def test_clean_scheduled_at_success(self, mock_datetime: MagicMock) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        data = {
            "scheduled_at_0": "2024-01-01",
            "scheduled_at_1": "00:00",
        }
        form = ScheduledEmailRescheduleForm(data=data)

        # Act
        result = form.is_valid()

        # Assert
        self.assertTrue(result)

    @patch("emails.forms.datetime", wraps=datetime)
    def test_clean_scheduled_at_failure(self, mock_datetime: MagicMock) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        data = {
            "scheduled_at_0": "2023-01-01",
            "scheduled_at_1": "00:00",
        }
        form = ScheduledEmailRescheduleForm(data=data)

        # Act
        result = form.is_valid()

        # Assert
        self.assertFalse(result)
        self.assertEqual(
            form.errors["scheduled_at"],
            ["Scheduled time cannot be in the past."],
        )
