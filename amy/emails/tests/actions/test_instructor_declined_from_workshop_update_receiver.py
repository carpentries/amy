from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from communityroles.models import CommunityRole, CommunityRoleConfig
from emails.actions.instructor_declined_from_workshop import (
    instructor_declined_from_workshop_strategy,
    instructor_declined_from_workshop_update_receiver,
    run_instructor_declined_from_workshop_strategy,
)
from emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)
from emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from emails.signals import (
    INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME,
    instructor_declined_from_workshop_update_signal,
)
from emails.utils import api_model_url
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from workshops.models import Event, Organization, Person, Tag
from workshops.tests.base import TestBase


class TestInstructorDeclinedFromWorkshopUpdateReceiver(TestCase):
    def setUp(self) -> None:
        host = Organization.objects.create(domain="test.com", fullname="Test")
        self.event = Event.objects.create(slug="test-event", host=host, start=date(2024, 8, 5), end=date(2024, 8, 5))
        self.person = Person.objects.create(email="test@example.org")
        self.recruitment = InstructorRecruitment.objects.create(event=self.event, notes="Test notes")
        self.signup = InstructorRecruitmentSignup.objects.create(recruitment=self.recruitment, person=self.person)

    def setUpEmailTemplate(self) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME,
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
            instructor_declined_from_workshop_update_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping " "instructor_declined_from_workshop_update"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = instructor_declined_from_workshop_update_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        instructor_declined_from_workshop_update_signal.connect(instructor_declined_from_workshop_update_receiver)
        new_receivers = instructor_declined_from_workshop_update_signal.receivers[:]

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
            generic_relation=self.signup,
        )

        # Act
        with patch("emails.actions.base_action.messages_action_updated") as mock_messages_action_updated:
            instructor_declined_from_workshop_update_signal.send(
                sender=self.signup,
                request=request,
                person_id=self.person.pk,
                event_id=self.event.pk,
                instructor_recruitment_id=self.recruitment.pk,
                instructor_recruitment_signup_id=self.signup.pk,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_updated.assert_called_once_with(
            request,
            INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_action_updated")
    @patch("emails.actions.instructor_declined_from_workshop.immediate_action")
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
            generic_relation=self.signup,
        )
        scheduled_at = datetime(2024, 12, 22, 12, 0, tzinfo=UTC)
        mock_immediate_action.return_value = scheduled_at

        # Act
        with patch("emails.actions.base_action.EmailController.update_scheduled_email") as mock_update_scheduled_email:
            instructor_declined_from_workshop_update_signal.send(
                sender=self.signup,
                request=request,
                person_id=self.person.pk,
                event_id=self.event.pk,
                instructor_recruitment_id=self.recruitment.pk,
                instructor_recruitment_signup_id=self.signup.pk,
            )

        # Assert
        mock_update_scheduled_email.assert_called_once_with(
            scheduled_email=scheduled_email,
            context_json=ContextModel(
                {
                    "person": api_model_url("person", self.person.pk),
                    "event": api_model_url("event", self.event.pk),
                    "instructor_recruitment_signup": api_model_url("instructorrecruitmentsignup", self.signup.pk),
                }
            ),
            scheduled_at=scheduled_at,
            to_header=[self.person.email],
            to_header_context_json=ToHeaderModel(
                [
                    SinglePropertyLinkModel(
                        api_uri=api_model_url("person", self.person.pk),
                        property="email",
                    ),
                ]
            ),
            generic_relation_obj=self.signup,
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
        signal = INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME

        # Act
        instructor_declined_from_workshop_update_signal.send(
            sender=self.signup,
            request=request,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=self.recruitment.pk,
            instructor_recruitment_signup_id=self.signup.pk,
        )

        # Assert
        mock_email_controller.update_scheduled_email.assert_not_called()
        signup = self.signup
        mock_logger.warning.assert_called_once_with(
            f"Scheduled email for signal {signal} and generic_relation_obj={signup!r} " "does not exist."
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.logger")
    @patch("emails.actions.base_action.EmailController")
    def test_multiple_previously_scheduled_emails(
        self, mock_email_controller: MagicMock, mock_logger: MagicMock
    ) -> None:
        # Arrange
        request = RequestFactory().get("/")
        signal = INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME
        template = self.setUpEmailTemplate()
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.signup,
        )
        ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=self.signup,
        )

        # Act
        instructor_declined_from_workshop_update_signal.send(
            sender=self.signup,
            request=request,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=self.recruitment.pk,
            instructor_recruitment_signup_id=self.signup.pk,
        )

        # Assert
        mock_email_controller.update_scheduled_email.assert_not_called()
        mock_logger.warning.assert_called_once_with(
            f"Too many scheduled emails for signal {signal} and "
            f"generic_relation_obj={self.signup!r}. Can't update them."
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_missing_recipients")
    def test_missing_recipients(self, mock_messages_missing_recipients: MagicMock) -> None:
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
            generic_relation=self.signup,
        )
        signal = INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME
        self.person.email = ""
        self.person.save()

        # Act
        instructor_declined_from_workshop_update_signal.send(
            sender=self.signup,
            request=request,
            person_id=self.person.pk,
            event_id=self.event.pk,
            instructor_recruitment_id=self.recruitment.pk,
            instructor_recruitment_signup_id=self.signup.pk,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)


class TestInstructorDeclinedFromWorkshopUpdateIntegration(TestBase):
    @override_settings(
        FLAGS={
            "INSTRUCTOR_RECRUITMENT": [("boolean", True)],
            "EMAIL_MODULE": [("boolean", True)],
        }
    )
    def test_integration(self) -> None:
        # Arrange
        self._setUpRoles()
        self._setUpTags()
        self._setUpAdministrators()
        self._setUpUsersAndLogin()
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create_user(
            username="test_test",
            personal="Test",
            family="User",
            email="test@user.com",
            password="test",
        )
        config = CommunityRoleConfig.objects.create(
            name="instructor",
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        CommunityRole.objects.create(
            config=config,
            person=person,
        )
        event = Event.objects.create(
            slug="test-event",
            host=host,
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            administrator=Organization.objects.get(domain="software-carpentry.org"),
        )
        event.tags.add(Tag.objects.get(name="SWC"))
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)
        signup = InstructorRecruitmentSignup.objects.create(recruitment=recruitment, person=person, state="d")

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_DECLINED_FROM_WORKSHOP_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ person.personal }}",
            body="Hello, {{ person.personal }}! Nice to meet **you**.",
        )

        request = RequestFactory().get("/")
        with patch("emails.actions.base_action.messages_action_scheduled") as mock_action_scheduled:
            run_instructor_declined_from_workshop_strategy(
                instructor_declined_from_workshop_strategy(signup),
                request,
                signup=signup,
                person_id=person.pk,
                event_id=event.pk,
                instructor_recruitment_id=recruitment.pk,
                instructor_recruitment_signup_id=signup.pk,
            )
        scheduled_email = ScheduledEmail.objects.get(template=template)

        url = reverse("instructorrecruitmentsignup_changestate", args=[signup.pk])
        payload = {"action": "decline"}

        # Act
        rv = self.client.post(url, payload)

        # Assert
        mock_action_scheduled.assert_called_once()
        self.assertEqual(rv.status_code, 302)
        scheduled_email.refresh_from_db()
        self.assertEqual(scheduled_email.state, ScheduledEmailStatus.SCHEDULED)
        # Ensure that last log is update (from 'scheduled' to 'scheduled')
        last_log = ScheduledEmailLog.objects.filter(scheduled_email=scheduled_email).order_by("created_at").last()
        assert last_log
        self.assertEqual(last_log.state_before, last_log.state_after)
