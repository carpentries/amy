from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.actions.instructor_task_created_for_workshop import (
    instructor_task_created_for_workshop_receiver,
)
from emails.models import EmailTemplate, ScheduledEmail
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import (
    INSTRUCTOR_TASK_CREATED_FOR_WORKSHOP_SIGNAL_NAME,
    instructor_task_created_for_workshop_signal,
)
from emails.utils import api_model_url, scalar_value_url
from workshops.models import Event, Organization, Person, Role, Tag, Task
from workshops.tests.base import TestBase


class TestInstructorTaskCreatedForWorkshopReceiver(TestCase):
    @patch("emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            instructor_task_created_for_workshop_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping "
                "instructor_task_created_for_workshop"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = instructor_task_created_for_workshop_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        instructor_task_created_for_workshop_signal.connect(
            instructor_task_created_for_workshop_receiver
        )
        new_receivers = instructor_task_created_for_workshop_signal.receivers[:]

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
        person = Person.objects.create(email="test@example.org")
        instructor_role = Role.objects.create(name="instructor")
        task = Task.objects.create(person=person, event=event, role=instructor_role)
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=instructor_task_created_for_workshop_signal.signal_name,
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
            instructor_task_created_for_workshop_signal.send(
                sender=task,
                request=request,
                task=task,
                person_id=person.pk,
                event_id=event.pk,
                task_id=task.pk,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_scheduled.assert_called_once_with(
            request,
            instructor_task_created_for_workshop_signal.signal_name,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_action_scheduled")
    @patch("emails.actions.instructor_task_created_for_workshop.immediate_action")
    def test_email_scheduled(
        self,
        mock_immediate_action: MagicMock,
        mock_messages_action_scheduled: MagicMock,
    ) -> None:
        # Arrange
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event", host=organization, administrator=organization
        )
        person = Person.objects.create(email="test@example.org")
        instructor_role = Role.objects.create(name="instructor")
        task = Task.objects.create(person=person, event=event, role=instructor_role)
        request = RequestFactory().get("/")

        NOW = datetime(2023, 6, 1, 10, 0, 0, tzinfo=UTC)
        mock_immediate_action.return_value = NOW + timedelta(hours=1)
        signal = instructor_task_created_for_workshop_signal.signal_name
        scheduled_at = NOW + timedelta(hours=1)

        # Act
        with patch(
            "emails.actions.base_action.EmailController.schedule_email"
        ) as mock_schedule_email:
            instructor_task_created_for_workshop_signal.send(
                sender=task,
                request=request,
                person_id=person.pk,
                event_id=event.pk,
                task_id=task.pk,
            )

        # Assert
        mock_schedule_email.assert_called_once_with(
            signal=signal,
            context_json=ContextModel(
                {
                    "person": api_model_url("person", person.pk),
                    "event": api_model_url("event", event.pk),
                    "task": api_model_url("task", task.pk),
                    "task_id": scalar_value_url("int", task.pk),
                }
            ),
            scheduled_at=scheduled_at,
            to_header=[person.email],
            to_header_context_json=ToHeaderModel(
                [
                    {
                        "api_uri": api_model_url("person", person.pk),
                        "property": "email",
                    }  # type: ignore
                ]
            ),
            generic_relation_obj=task,
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
        person = Person.objects.create()  # no email will cause missing recipients error
        instructor_role = Role.objects.create(name="instructor")
        task = Task.objects.create(person=person, event=event, role=instructor_role)
        request = RequestFactory().get("/")
        signal = instructor_task_created_for_workshop_signal.signal_name

        # Act
        instructor_task_created_for_workshop_signal.send(
            sender=task,
            request=request,
            person_id=person.pk,
            event_id=event.pk,
            task_id=task.pk,
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
        person = Person.objects.create(email="test@example.org")
        instructor_role = Role.objects.create(name="instructor")
        task = Task.objects.create(person=person, event=event, role=instructor_role)
        request = RequestFactory().get("/")
        signal = instructor_task_created_for_workshop_signal.signal_name

        # Act
        instructor_task_created_for_workshop_signal.send(
            sender=task,
            request=request,
            person_id=person.pk,
            event_id=event.pk,
            task_id=task.pk,
        )

        # Assert
        mock_messages_missing_template.assert_called_once_with(request, signal)


class TestInstructorTaskCreatedForWorkshopReceiverIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_TASK_CREATED_FOR_WORKSHOP_SIGNAL_NAME,
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
            bluesky="@purdy_kelsi.bsky.social",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        instructor_role = Role.objects.get(name="instructor")

        url = reverse("task_add")
        payload = {
            "task-event": event.pk,
            "task-person": instructor.pk,
            "task-role": instructor_role.pk,
        }

        # Act
        rv = self.client.post(url, payload)

        # Assert
        self.assertEqual(rv.status_code, 302)
        ScheduledEmail.objects.get(template=template)
