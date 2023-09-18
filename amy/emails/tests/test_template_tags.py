from unittest.mock import MagicMock

from django.test import TestCase

from emails.models import ScheduledEmailStatus
from emails.templatetags.emails import (
    allowed_actions_for_status,
    model_documentation_link,
)


class TestModelDocumentationLink(TestCase):
    def test_model_documentation_link__valid_model(self) -> None:
        # Arrange
        # Real models are replaced with their metaclass BaseModel, so the tests don't
        # work with real models and instead mocks are used.
        model = MagicMock()
        model.__class__.__name__ = "Person"

        # Act
        link = model_documentation_link(model)

        # Assert
        self.assertEqual(
            link,
            "https://carpentries.github.io/amy/amy_database_structure/#persons",
        )

    def test_model_documentation_link__invalid_model(self) -> None:
        # Arrange
        # Real models are replaced with their metaclass BaseModel, so the tests don't
        # work with real models and instead mocks are used.
        model = MagicMock()
        # Badge is not in the mapping yet
        model.__class__.__name__ = "Badge"

        # Act
        link = model_documentation_link(model)

        # Assert
        self.assertEqual(link, "")


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
        self.assertEqual(result2, ["reschedule"])
