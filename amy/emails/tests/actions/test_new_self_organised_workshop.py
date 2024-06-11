from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.actions import new_self_organised_workshop_receiver
from emails.actions.new_self_organised_workshop import new_self_organised_workshop_check
from emails.models import EmailTemplate, ScheduledEmail
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import new_self_organised_workshop_signal
from emails.utils import api_model_url, scalar_value_none, scalar_value_url
from extrequests.models import SelfOrganisedSubmission
from workshops.models import Event, Language, Organization, Tag
from workshops.tests.base import TestBase


class TestNewSelfOrganisedWorkshopCheck(TestCase):
    def setUp(self) -> None:
        self.submission = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
        )
        self.self_org = Organization.objects.get(domain="self-organized")
        self.swc_org = Organization.objects.create(
            domain="software-carpentry.org", fullname="Software Carpentry"
        )
        self.swc_tag = Tag.objects.create(name="SWC")
        self.event_start = date.today() + timedelta(days=30)

    def test_check_not_all_conditions(self) -> None:
        # Arrange
        event = Event.objects.create(
            slug="2024-05-31-test-event",
            host=self.swc_org,
            sponsor=self.swc_org,
            administrator=self.self_org,
            start=self.event_start,
        )
        event.tags.add(self.swc_tag)

        # Missing link with submission
        # self.submission.event = event  # type: ignore
        # self.submission.save()

        # Act
        result = new_self_organised_workshop_check(event)

        # Assert
        self.assertFalse(result)

    def test_check_all_conditions(self) -> None:
        # Arrange
        event = Event.objects.create(
            slug="2024-05-31-test-event",
            host=self.swc_org,
            sponsor=self.swc_org,
            administrator=self.self_org,
            start=self.event_start,
        )
        event.tags.add(self.swc_tag)
        self.submission.event = event  # type: ignore
        self.submission.save()

        # Act
        result = new_self_organised_workshop_check(event)

        # Assert
        self.assertTrue(result)


class TestNewSelfOrganisedWorkshopReceiver(TestCase):
    @patch("emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            new_self_organised_workshop_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping "
                "new_self_organised_workshop"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = new_self_organised_workshop_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        new_self_organised_workshop_signal.connect(new_self_organised_workshop_receiver)
        new_receivers = new_self_organised_workshop_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_action_triggered(self) -> None:
        # Arrange
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event", host=organization, administrator=organization
        )
        submission = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
            event=event,
        )
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=new_self_organised_workshop_signal.signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        # Act
        with patch(
            "emails.actions.base_action.messages_action_scheduled"
        ) as mock_messages_action_scheduled:
            new_self_organised_workshop_signal.send(
                sender=event,
                request=request,
                event=event,
                self_organised_submission=submission,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_scheduled.assert_called_once_with(
            request,
            new_self_organised_workshop_signal.signal_name,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_action_scheduled")
    @patch("emails.actions.new_self_organised_workshop.immediate_action")
    def test_email_scheduled(
        self,
        mock_immediate_action: MagicMock,
        mock_messages_action_scheduled: MagicMock,
    ) -> None:
        # Arrange
        NOW = datetime(2023, 6, 1, 10, 0, 0, tzinfo=UTC)
        mock_immediate_action.return_value = NOW + timedelta(hours=1)
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event", host=organization, administrator=organization
        )
        submission = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
            event=event,
        )
        request = RequestFactory().get("/")
        signal = new_self_organised_workshop_signal.signal_name
        scheduled_at = NOW + timedelta(hours=1)

        # Act
        with patch(
            "emails.actions.base_action.EmailController.schedule_email"
        ) as mock_schedule_email:
            new_self_organised_workshop_signal.send(
                sender=event,
                request=request,
                event=event,
                self_organised_submission=submission,
            )

        # Assert
        mock_schedule_email.assert_called_once_with(
            signal=signal,
            context_json=ContextModel(
                {
                    "assignee": scalar_value_none(),
                    "workshop_host": api_model_url(
                        "organization",
                        organization.pk,  # type: ignore
                    ),
                    "event": api_model_url("event", event.pk),
                    "short_notice": scalar_value_url("bool", "False"),
                    "self_organised_submission": api_model_url(
                        "selforganisedsubmission", submission.pk
                    ),
                }
            ),
            scheduled_at=scheduled_at,
            to_header=[submission.email],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url(
                            "selforganisedsubmission", submission.pk
                        ),
                        "property": "email",
                    }  # type: ignore
                ]
            ),
            generic_relation_obj=event,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_missing_recipients")
    def test_missing_recipients(
        self, mock_messages_missing_recipients: MagicMock
    ) -> None:
        # Arrange
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event", host=organization, administrator=organization
        )
        submission = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="",  # intentionally empty
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
            event=event,
        )
        request = RequestFactory().get("/")
        signal = new_self_organised_workshop_signal.signal_name

        # Act
        new_self_organised_workshop_signal.send(
            sender=event,
            request=request,
            event=event,
            self_organised_submission=submission,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_missing_template")
    def test_missing_template(self, mock_messages_missing_template: MagicMock) -> None:
        # Arrange
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event", host=organization, administrator=organization
        )
        submission = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
            event=event,
        )
        request = RequestFactory().get("/")
        signal = new_self_organised_workshop_signal.signal_name

        # Act
        new_self_organised_workshop_signal.send(
            sender=event,
            request=request,
            event=event,
            self_organised_submission=submission,
        )

        # Assert
        mock_messages_missing_template.assert_called_once_with(request, signal)


class TestNewSelfOrganisedWorkshopIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpUsersAndLogin()
        self._setUpTags()
        self._setUpRoles()
        submission = SelfOrganisedSubmission.objects.create(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url="",
            workshop_format="",
            workshop_format_other="",
            workshop_types_other_explain="",
            language=Language.objects.get(name="English"),
        )
        self_org = Organization.objects.get(domain="self-organized")
        swc_org = Organization.objects.create(
            domain="software-carpentry.org", fullname="Software Carpentry"
        )
        start = date.today() + timedelta(days=30)
        data = {
            "slug": "2024-05-31-test-event",
            "host": swc_org.pk,
            "sponsor": swc_org.pk,
            "administrator": self_org.pk,
            "tags": [Tag.objects.get(name="SWC").pk],
            "start": f"{start:%Y-%m-%d}",
        }
        url = reverse("selforganisedsubmission_accept_event", args=[submission.pk])

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=new_self_organised_workshop_signal.signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ person.personal }}",
            body="Hello, {{ person.personal }}! Nice to meet **you**.",
        )

        # Act
        rv = self.client.post(url, data=data)

        # Assert
        self.assertEqual(rv.status_code, 302)
        Event.objects.get(slug="2024-05-31-test-event")
        ScheduledEmail.objects.get(template=template)
