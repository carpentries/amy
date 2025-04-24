from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, call, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.actions.instructor_task_created_for_workshop import (
    instructor_task_created_for_workshop_cancel_receiver,
    instructor_task_created_for_workshop_strategy,
    run_instructor_task_created_for_workshop_strategy,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.signals import (
    INSTRUCTOR_TASK_CREATED_FOR_WORKSHOP_SIGNAL_NAME,
    instructor_task_created_for_workshop_cancel_signal,
)
from workshops.models import Event, Organization, Person, Role, Tag, Task
from workshops.tests.base import TestBase


class TestInstructorTaskCreatedForWorkshopCancelReceiver(TestCase):
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
            signal=INSTRUCTOR_TASK_CREATED_FOR_WORKSHOP_SIGNAL_NAME,
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
            instructor_task_created_for_workshop_cancel_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping "
                "instructor_task_created_for_workshop_cancel"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = (
            instructor_task_created_for_workshop_cancel_signal.receivers[:]
        )

        # Act
        # attempt to connect the receiver
        instructor_task_created_for_workshop_cancel_signal.connect(
            instructor_task_created_for_workshop_cancel_receiver
        )
        new_receivers = instructor_task_created_for_workshop_cancel_signal.receivers[:]

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
            generic_relation=self.task,
        )

        # Act
        with patch(
            "emails.actions.base_action.messages_action_cancelled"
        ) as mock_messages_action_cancelled:
            instructor_task_created_for_workshop_cancel_signal.send(
                sender=self.task,
                request=request,
                task=self.task,
                person_id=self.person.pk,
                event_id=self.event.pk,
                task_id=self.task.pk,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_cancelled.assert_called_once_with(
            request,
            INSTRUCTOR_TASK_CREATED_FOR_WORKSHOP_SIGNAL_NAME,
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
            generic_relation=self.task,
        )

        # Act
        with patch(
            "emails.actions.base_action.EmailController.cancel_email"
        ) as mock_cancel_email:
            instructor_task_created_for_workshop_cancel_signal.send(
                sender=self.task,
                request=request,
                task=self.task,
                person_id=self.person.pk,
                event_id=self.event.pk,
                task_id=self.task.pk,
                instructor_recruitment_id=None,
                instructor_recruitment_signup_id=None,
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
            generic_relation=self.task,
        )
        scheduled_email2 = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.task,
        )

        # Act
        with patch(
            "emails.actions.base_action.EmailController.cancel_email"
        ) as mock_cancel_email:
            instructor_task_created_for_workshop_cancel_signal.send(
                sender=self.task,
                request=request,
                task=self.task,
                person_id=self.person.pk,
                event_id=self.event.pk,
                task_id=self.task.pk,
                instructor_recruitment_id=None,
                instructor_recruitment_signup_id=None,
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


class TestInstructorTaskCreatedForWorkshopCancelIntegration(TestBase):
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
            mastodon="https://convo.casa/@trewq",
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
            run_instructor_task_created_for_workshop_strategy(
                instructor_task_created_for_workshop_strategy(task),
                request,
                task=task,
                person_id=task.person.pk,
                event_id=task.event.pk,
                task_id=task.pk,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("task_delete", args=[task.pk])

        # Act
        rv = self.client.post(url)

        # Arrange
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.CANCELLED)
