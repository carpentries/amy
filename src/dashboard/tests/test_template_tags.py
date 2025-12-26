from django.conf import settings
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.test import RequestFactory, TestCase

from src.dashboard.templatetags.notifications import message_allowed
from src.workshops.models import Person


class TestMessageAllowed(TestCase):
    def test_notification_not_tagged_for_admins_displays_for_admins(self) -> None:
        # Arrange
        person = Person.objects.create_superuser("admin", "admin", "admin", "admin@example.org", "admin")
        request = RequestFactory().get("/")
        request.user = person
        message = Message(constants.INFO, "Test message", extra_tags="")

        # Act
        result = message_allowed(message, request)

        # Assert
        self.assertTrue(result)

    def test_notification_not_tagged_for_admins_displays_for_instructors(self) -> None:
        # Arrange
        person = Person.objects.create_user("user", "user", "user", "user@example.org", "user")
        request = RequestFactory().get("/")
        request.user = person
        message = Message(constants.INFO, "Test message", extra_tags="")

        # Act
        result = message_allowed(message, request)

        # Assert
        self.assertTrue(result)

    def test_notification_tagged_for_admins_displays_for_admins(self) -> None:
        # Arrange
        person = Person.objects.create_superuser("admin", "admin", "admin", "admin@example.org", "admin")
        request = RequestFactory().get("/")
        request.user = person
        message = Message(constants.INFO, "Test message", extra_tags=settings.ONLY_FOR_ADMINS_TAG)

        # Act
        result = message_allowed(message, request)

        # Assert
        self.assertTrue(result)

    def test_notification_tagged_for_admins_doesnt_display_for_instructors(
        self,
    ) -> None:
        # Arrange
        person = Person.objects.create_user("user", "user", "user", "user@example.org", "user")
        request = RequestFactory().get("/")
        request.user = person
        message = Message(constants.INFO, "Test message", extra_tags=settings.ONLY_FOR_ADMINS_TAG)

        # Act
        result = message_allowed(message, request)

        # Assert
        self.assertFalse(result)
