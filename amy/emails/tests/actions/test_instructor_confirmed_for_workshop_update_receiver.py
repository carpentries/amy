from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.actions.instructor_confirmed_for_workshop import (
    instructor_confirmed_for_workshop_strategy,
    instructor_confirmed_for_workshop_update_receiver,
    run_instructor_confirmed_for_workshop_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import (
    INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME,
    instructor_confirmed_for_workshop_update_signal,
)
from emails.utils import api_model_url, scalar_value_none
from workshops.forms import PersonForm
from workshops.models import Event, Organization, Person, Role, Tag, Task
from workshops.tests.base import TestBase


class TestInstructorConfirmedForWorkshopUpdateReceiver(TestCase):
    def setUp(self) -> None:
        host = Organization.objects.create(domain="test.com", fullname="Test")
        self.event = Event.objects.create(
            slug="test-event", host=host, start=date(2024, 8, 5), end=date(2024, 8, 5)
        )
        self.person = Person.objects.create(email="test@example.org")
        instructor = Role.objects.create(name="instructor")
        self.task = Task.objects.create(
            role=instructor, person=self.person, event=self.event
        )

    def setUpEmailTemplate(self) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME,
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
            instructor_confirmed_for_workshop_update_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping "
                "instructor_confirmed_for_workshop_update"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = instructor_confirmed_for_workshop_update_signal.receivers[
            :
        ]

        # Act
        # attempt to connect the receiver
        instructor_confirmed_for_workshop_update_signal.connect(
            instructor_confirmed_for_workshop_update_receiver
        )
        new_receivers = instructor_confirmed_for_workshop_update_signal.receivers[:]

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
            generic_relation=self.person,
        )

        # Act
        with patch(
            "emails.actions.base_action.messages_action_updated"
        ) as mock_messages_action_updated:
            instructor_confirmed_for_workshop_update_signal.send(
                sender=self.task,
                request=request,
                task=self.task,
                person_id=self.person.pk,
                event_id=self.event.pk,
                instructor_recruitment_id=None,
                instructor_recruitment_signup_id=None,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_updated.assert_called_once_with(
            request,
            INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_action_updated")
    @patch("emails.actions.instructor_confirmed_for_workshop.immediate_action")
    def test_email_updated(
        self,
        mock_immediate_action: MagicMock,
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
            generic_relation=self.person,
        )
        scheduled_at = datetime(2024, 8, 5, 12, 0, tzinfo=UTC)
        mock_immediate_action.return_value = scheduled_at

        # Act
        with patch(
            "emails.actions.base_action.EmailController.update_scheduled_email"
        ) as mock_update_scheduled_email:
            instructor_confirmed_for_workshop_update_signal.send(
                sender=self.task,
                request=request,
                task=self.task,
                person_id=self.person.pk,
                event_id=self.event.pk,
                instructor_recruitment_id=None,
                instructor_recruitment_signup_id=None,
            )

        # Assert
        mock_update_scheduled_email.assert_called_once_with(
            scheduled_email=scheduled_email,
            context_json=ContextModel(
                {
                    "person": api_model_url("person", self.person.pk),
                    "event": api_model_url("event", self.event.pk),
                    "instructor_recruitment_signup": scalar_value_none(),
                }
            ),
            scheduled_at=scheduled_at,
            to_header=[self.person.email],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", self.person.pk),
                        "property": "email",
                    },  # type: ignore
                ]
            ),
            generic_relation_obj=self.person,
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
        signal = INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME
        person = self.person

        # Act
        instructor_confirmed_for_workshop_update_signal.send(
            sender=self.task,
            request=request,
            task=self.task,
            person_id=person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=None,
            instructor_recruitment_signup_id=None,
        )

        # Assert
        mock_email_controller.update_scheduled_email.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            f"Scheduled email for signal {signal} and generic_relation_obj={person!r} "
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
        signal = INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME
        template = self.setUpEmailTemplate()
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.person,
        )
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.person,
        )
        person = self.person

        # Act
        instructor_confirmed_for_workshop_update_signal.send(
            sender=self.task,
            request=request,
            task=self.task,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=None,
            instructor_recruitment_signup_id=None,
        )

        # Assert
        mock_email_controller.update_scheduled_email.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            f"Too many scheduled emails for signal {signal} and "
            f"generic_relation_obj={person!r}. Can't update them."
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
            generic_relation=self.person,
        )
        signal = INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME
        self.person.email = ""
        self.person.save()

        # Act
        instructor_confirmed_for_workshop_update_signal.send(
            sender=self.task,
            request=request,
            task=self.task,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=None,
            instructor_recruitment_signup_id=None,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)


class TestInstructorConfirmedForWorkshopUpdateIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_CONFIRMED_FOR_WORKSHOP_SIGNAL_NAME,
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
            slug="2024-08-05-test-event",
            host=host_organization,
            administrator=ttt_organization,
            start=date.today() + timedelta(days=30),
        )
        event.tags.set([Tag.objects.get(name="SWC")])

        instructor = Person.objects.create(
            personal="Kelsi",
            middle="",
            family="Purdy",
            username="purdy_kelsi",
            email="purdy.kelsi@example.com",
            secondary_email="notused@amy.org",
            gender="F",
            airport=self.airport_0_0,
            github="",
            twitter="",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        instructor_role = Role.objects.get(name="instructor")
        task = Task.objects.create(event=event, person=instructor, role=instructor_role)

        request = RequestFactory().get("/")
        with patch(
            "emails.actions.base_action.messages_action_scheduled"
        ) as mock_action_scheduled:
            run_instructor_confirmed_for_workshop_strategy(
                instructor_confirmed_for_workshop_strategy(task),
                request,
                task=task,
                person_id=task.person.pk,
                event_id=task.event.pk,
                instructor_recruitment_id=None,
                instructor_recruitment_signup_id=None,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("person_edit", args=[instructor.pk])
        new_email = "fake_email@example.org"
        data = PersonForm(instance=instructor).initial
        data.update({"email": new_email, "github": "", "twitter": ""})

        # Act
        rv = self.client.post(url, data)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.SCHEDULED)
        self.assertEqual(scheduled_email.to_header, [new_email])
