from datetime import UTC, datetime
from unittest.mock import MagicMock, call, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.actions.instructor_badge_awarded import (
    instructor_badge_awarded_cancel_receiver,
    instructor_badge_awarded_strategy,
    run_instructor_badge_awarded_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.signals import (
    INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
    instructor_badge_awarded_cancel_signal,
)
from workshops.models import Award, Badge, Person
from workshops.tests.base import TestBase


class TestInstructorBadgeAwardedCancelReceiver(TestCase):
    def setUp(self) -> None:
        self.badge = Badge.objects.create(name="instructor")
        self.person = Person.objects.create(email="test@example.org")
        self.award = Award.objects.create(badge=self.badge, person=self.person)

    def setUpEmailTemplate(self) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

    @patch("emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            instructor_badge_awarded_cancel_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping " "instructor_badge_awarded_cancel"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = instructor_badge_awarded_cancel_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        instructor_badge_awarded_cancel_signal.connect(instructor_badge_awarded_cancel_receiver)
        new_receivers = instructor_badge_awarded_cancel_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_action_triggered(self) -> None:
        # Arrange
        request = RequestFactory().get("/")

        template = self.setUpEmailTemplate()
        scheduled_email = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.award,
        )

        # Act
        with patch("emails.actions.base_action.messages_action_cancelled") as mock_messages_action_cancelled:
            instructor_badge_awarded_cancel_signal.send(
                sender=self.award,
                request=request,
                person_id=self.person.pk,
                award_id=self.award.pk,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_cancelled.assert_called_once_with(
            request,
            INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_action_cancelled")
    def test_email_cancelled(
        self,
        mock_messages_action_cancelled: MagicMock,
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        template = self.setUpEmailTemplate()
        scheduled_email = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.award,
        )

        # Act
        with patch("emails.actions.base_action.EmailController.cancel_email") as mock_cancel_email:
            instructor_badge_awarded_cancel_signal.send(
                sender=self.award,
                request=request,
                person_id=self.person.pk,
                award_id=self.award.pk,
            )

        # Assert
        mock_cancel_email.assert_called_once_with(
            scheduled_email=scheduled_email,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_action_cancelled")
    def test_multiple_emails_cancelled(
        self,
        mock_messages_action_cancelled: MagicMock,
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        template = self.setUpEmailTemplate()
        scheduled_email1 = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.award,
        )
        scheduled_email2 = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.award,
        )

        # Act
        with patch("emails.actions.base_action.EmailController.cancel_email") as mock_cancel_email:
            instructor_badge_awarded_cancel_signal.send(
                sender=self.person,
                request=request,
                award_id=self.award.pk,
                person_id=self.person.pk,
            )

        # Assert
        mock_cancel_email.assert_has_calls(
            [
                call(
                    scheduled_email=scheduled_email1,
                    author=None,
                ),
                call(
                    scheduled_email=scheduled_email2,
                    author=None,
                ),
            ]
        )


class TestInstructorBadgeAwardedCancelIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.instructor_badge_awarded.EmailController.add_attachment")
    def test_integration(self, mock_add_attachment: MagicMock) -> None:
        # Arrange
        mock_add_attachment.return_value = None
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()
        badge = Badge.objects.get(name="instructor")
        person = Person.objects.create(
            personal="Kelsi",
            middle="",
            family="Purdy",
            username="purdy_kelsi",
            email="purdy.kelsi@example.com",
            secondary_email="notused@amy.org",
            gender="F",
            airport_iata="CDG",
            github="purdy_kelsi",
            twitter="purdy_kelsi",
            bluesky="@purdy_kelsi.bsky.social",
            mastodon="http://kelsipurdy.com/",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        award = Award.objects.create(badge=badge, person=person)

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )

        request = RequestFactory().get("/")

        with patch("emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_instructor_badge_awarded_strategy(
                instructor_badge_awarded_strategy(award, person),
                request,
                person,
                award_id=award.pk,
                person_id=person.pk,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("award_delete", args=[award.pk])

        # Act
        rv = self.client.post(url)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
