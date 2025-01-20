from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.actions import recruit_helpers_update_receiver
from emails.actions.recruit_helpers import (
    recruit_helpers_strategy,
    run_recruit_helpers_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import RECRUIT_HELPERS_SIGNAL_NAME, recruit_helpers_update_signal
from emails.utils import api_model_url, scalar_value_none
from workshops.models import Event, Organization, Person, Role, Tag, Task
from workshops.tests.base import TestBase


class TestRecruitHelpersUpdateReceiver(TestCase):
    def setUp(self) -> None:
        self.ttt_organization = Organization.objects.create(
            domain="carpentries.org", fullname="Instructor Training"
        )
        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.create(domain="example.com", fullname="Example"),
            administrator=self.ttt_organization,
            start=date.today() + timedelta(days=30),
        )
        ttt_tag = Tag.objects.create(name="TTT")
        self.event.tags.add(ttt_tag)
        instructor_role = Role.objects.create(name="instructor")
        self.instructor = Person.objects.create(
            personal="Test", family="Test", email="test1@example.org", username="test1"
        )
        host_role = Role.objects.create(name="host")
        self.host = Person.objects.create(
            personal="Test", family="Test", email="test2@example.org", username="test3"
        )
        Task.objects.create(
            event=self.event, person=self.instructor, role=instructor_role
        )
        Task.objects.create(event=self.event, person=self.host, role=host_role)

    def setUpEmailTemplate(self) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template",
            signal=RECRUIT_HELPERS_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

    @patch("emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            recruit_helpers_update_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping recruit_helpers_update"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = recruit_helpers_update_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        recruit_helpers_update_signal.connect(recruit_helpers_update_receiver)
        new_receivers = recruit_helpers_update_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_action_triggered(self) -> None:
        # Arrange
        request = RequestFactory().get("/")

        template = self.setUpEmailTemplate()
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.event,
        )

        # Act
        with patch(
            "emails.actions.base_action.messages_action_updated"
        ) as mock_messages_action_updated:
            recruit_helpers_update_signal.send(
                sender=self.event,
                request=request,
                event=self.event,
                event_start_date=self.event.start,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_updated.assert_called_once_with(
            request,
            RECRUIT_HELPERS_SIGNAL_NAME,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_action_updated")
    @patch("emails.actions.recruit_helpers.shift_date_and_apply_current_utc_time")
    def test_email_updated(
        self,
        mock_shift_date_and_apply_current_utc_time: MagicMock,
        mock_messages_action_updated: MagicMock,
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
            generic_relation=self.event,
        )
        scheduled_at = datetime(2023, 8, 5, 12, 0, tzinfo=UTC)
        mock_shift_date_and_apply_current_utc_time.return_value = scheduled_at

        # Act
        with patch(
            "emails.actions.base_action.EmailController.update_scheduled_email"
        ) as mock_update_scheduled_email:
            recruit_helpers_update_signal.send(
                sender=self.event,
                request=request,
                event=self.event,
                event_start_date=self.event.start,
            )

        # Assert
        mock_update_scheduled_email.assert_called_once_with(
            scheduled_email=scheduled_email,
            context_json=ContextModel(
                {
                    "assignee": scalar_value_none(),
                    "event": api_model_url("event", self.event.pk),
                    "instructors": [api_model_url("person", self.instructor.pk)],
                    "hosts": [api_model_url("person", self.host.pk)],
                }
            ),
            scheduled_at=scheduled_at,
            to_header=[self.instructor.email, self.host.email],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.instructor.pk),
                        "property": "email",
                    },
                    {
                        "api_uri": api_model_url("person", self.host.pk),
                        "property": "email",
                    },
                ]  # type: ignore
            ),
            generic_relation_obj=self.event,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.logger")
    @patch("emails.actions.base_action.EmailController")
    def test_previously_scheduled_email_not_existing(
        self, mock_email_controller: MagicMock, mock_logger: MagicMock
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal = RECRUIT_HELPERS_SIGNAL_NAME
        event = self.event

        # Act
        recruit_helpers_update_signal.send(
            sender=self.event,
            request=request,
            event=self.event,
            event_start_date=self.event.start,
        )

        # Assert
        mock_email_controller.update_scheduled_email.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            f"Scheduled email for signal {signal} and generic_relation_obj={event!r} "
            "does not exist."
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.logger")
    @patch("emails.actions.base_action.EmailController")
    def test_multiple_previously_scheduled_emails(
        self, mock_email_controller: MagicMock, mock_logger: MagicMock
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal = RECRUIT_HELPERS_SIGNAL_NAME
        template = self.setUpEmailTemplate()
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.event,
        )
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.event,
        )
        event = self.event

        # Act
        recruit_helpers_update_signal.send(
            sender=self.event,
            request=request,
            event=self.event,
            event_start_date=self.event.start,
        )

        # Assert
        mock_email_controller.update_scheduled_email.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            f"Too many scheduled emails for signal {signal} and "
            f"generic_relation_obj={event!r}. Can't update them."
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_missing_recipients")
    def test_missing_recipients(
        self, mock_messages_missing_recipients: MagicMock
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        template = self.setUpEmailTemplate()
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.event,
        )
        signal = RECRUIT_HELPERS_SIGNAL_NAME
        self.instructor.email = ""
        self.instructor.save()
        self.host.email = ""
        self.host.save()

        # Act
        recruit_helpers_update_signal.send(
            sender=self.event,
            request=request,
            event=self.event,
            event_start_date=self.event.start,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)


class TestRecruitHelpersUpdateIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=RECRUIT_HELPERS_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings",
            body="Hello! Nice to meet **you**.",
        )

        ttt_organization = Organization.objects.create(
            domain="carpentries.org", fullname="Instructor Training"
        )
        host_organization = Organization.objects.create(
            domain="example.com", fullname="Example"
        )
        event = Event.objects.create(
            slug="2023-09-14-test-event",
            host=host_organization,
            administrator=ttt_organization,
            start=date.today() + timedelta(days=30),
        )
        swc_tag = Tag.objects.get(name="SWC")
        event.tags.set([swc_tag])

        instructor1 = Person.objects.create(
            personal="Kelsi",
            middle="",
            family="Purdy",
            username="purdy_kelsi",
            email="purdy.kelsi@example.com",
            secondary_email="notused@amy.org",
            gender="F",
            airport=self.airport_0_0,
            github="purdy_kelsi",
            twitter="purdy_kelsi",
            bluesky="@purdy_kelsi.bsky.social",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        host = Person.objects.create(
            personal="Jayden",
            middle="",
            family="Deckow",
            username="deckow_jayden",
            email="deckow.jayden@example.com",
            secondary_email="notused@example.org",
            gender="M",
            airport=self.airport_0_50,
            github="deckow_jayden",
            twitter="deckow_jayden",
            bluesky="@deckow_jayden.bsky.social",
            url="http://jaydendeckow.com/",
            affiliation="UFlo",
            occupation="Staff",
            orcid="0000-0000-0001",
            is_active=True,
        )
        instructor_role = Role.objects.get(name="instructor")
        Task.objects.create(event=event, person=instructor1, role=instructor_role)
        host_role = Role.objects.get(name="host")
        Task.objects.create(event=event, person=host, role=host_role)

        request = RequestFactory().get("/")
        with patch(
            "emails.actions.base_action.messages_action_scheduled"
        ) as mock_action_scheduled:
            run_recruit_helpers_strategy(
                recruit_helpers_strategy(event),
                request,
                event,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("event_edit", args=[event.slug])
        data = {
            "slug": event.slug,
            "host": event.host.pk,
            "sponsor": event.host.pk,
            "administrator": event.administrator.pk,  # type: ignore
            "start": date.today() + timedelta(days=60),
            "tags": [swc_tag.pk],
        }

        # Act
        rv = self.client.post(url, data)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.SCHEDULED)
        self.assertEqual(
            # runs the same day
            scheduled_email.scheduled_at.date(),
            date.today() + timedelta(days=60) - timedelta(days=21),
        )
