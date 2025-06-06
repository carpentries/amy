from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from communityroles.models import CommunityRole, CommunityRoleConfig
from emails.actions.instructor_signs_up_for_workshop import (
    instructor_signs_up_for_workshop_receiver,
)
from emails.models import EmailTemplate, ScheduledEmail
from emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from emails.signals import instructor_signs_up_for_workshop_signal
from emails.utils import api_model_url
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from workshops.models import Event, Organization, Person
from workshops.tests.base import TestBase, consent_to_all_required_consents


class TestInstructorSignsUpForWorkshopReceiver(TestCase):
    @patch("emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            instructor_signs_up_for_workshop_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping " "instructor_signs_up_for_workshop"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = instructor_signs_up_for_workshop_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        instructor_signs_up_for_workshop_signal.connect(instructor_signs_up_for_workshop_receiver)
        new_receivers = instructor_signs_up_for_workshop_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_action_triggered(self) -> None:
        # Arrange
        organization = Organization.objects.all()[0]
        event = Event.objects.create(slug="test-event", host=organization, administrator=organization)
        recruitment = InstructorRecruitment.objects.create(event=event, notes="Test notes")
        person = Person.objects.create(email="test@example.org")
        signup = InstructorRecruitmentSignup.objects.create(recruitment=recruitment, person=person)
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=instructor_signs_up_for_workshop_signal.signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        # Act
        with patch("emails.actions.base_action.messages_action_scheduled") as mock_messages_action_scheduled:
            instructor_signs_up_for_workshop_signal.send(
                sender=signup,
                request=request,
                person_id=signup.person.pk,
                event_id=signup.recruitment.event.pk,
                instructor_recruitment_id=signup.recruitment.pk,
                instructor_recruitment_signup_id=signup.pk,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_scheduled.assert_called_once_with(
            request,
            instructor_signs_up_for_workshop_signal.signal_name,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_action_scheduled")
    @patch("emails.actions.instructor_signs_up_for_workshop.immediate_action")
    def test_email_scheduled(
        self,
        mock_immediate_action: MagicMock,
        mock_messages_action_scheduled: MagicMock,
    ) -> None:
        # Arrange
        organization = Organization.objects.all()[0]
        event = Event.objects.create(slug="test-event", host=organization, administrator=organization)
        recruitment = InstructorRecruitment.objects.create(event=event, notes="Test notes")
        person = Person.objects.create(email="test@example.org")
        signup = InstructorRecruitmentSignup.objects.create(recruitment=recruitment, person=person)
        request = RequestFactory().get("/")

        NOW = datetime(2023, 6, 1, 10, 0, 0, tzinfo=UTC)
        mock_immediate_action.return_value = NOW + timedelta(hours=1)
        signal = instructor_signs_up_for_workshop_signal.signal_name
        scheduled_at = NOW + timedelta(hours=1)

        # Act
        with patch("emails.actions.base_action.EmailController.schedule_email") as mock_schedule_email:
            instructor_signs_up_for_workshop_signal.send(
                sender=signup,
                request=request,
                person_id=signup.person.pk,
                event_id=signup.recruitment.event.pk,
                instructor_recruitment_id=signup.recruitment.pk,
                instructor_recruitment_signup_id=signup.pk,
            )

        # Assert
        mock_schedule_email.assert_called_once_with(
            signal=signal,
            context_json=ContextModel(
                {
                    "person": api_model_url("person", person.pk),
                    "event": api_model_url("event", event.pk),
                    "instructor_recruitment_signup": api_model_url("instructorrecruitmentsignup", signup.pk),
                }
            ),
            scheduled_at=scheduled_at,
            to_header=[person.email],
            to_header_context_json=ToHeaderModel(
                [
                    SinglePropertyLinkModel(
                        api_uri=api_model_url("person", person.pk),
                        property="email",
                    ),
                ]
            ),
            generic_relation_obj=signup,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_missing_recipients")
    def test_missing_recipients(self, mock_messages_missing_recipients: MagicMock) -> None:
        # Arrange
        organization = Organization.objects.all()[0]
        event = Event.objects.create(slug="test-event", host=organization, administrator=organization)
        recruitment = InstructorRecruitment.objects.create(event=event, notes="Test notes")
        person = Person.objects.create()  # no email will cause missing recipients error
        signup = InstructorRecruitmentSignup.objects.create(recruitment=recruitment, person=person)
        request = RequestFactory().get("/")
        signal = instructor_signs_up_for_workshop_signal.signal_name

        # Act
        instructor_signs_up_for_workshop_signal.send(
            sender=signup,
            request=request,
            person_id=signup.person.pk,
            event_id=signup.recruitment.event.pk,
            instructor_recruitment_id=signup.recruitment.pk,
            instructor_recruitment_signup_id=signup.pk,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_missing_template")
    def test_missing_template(self, mock_messages_missing_template: MagicMock) -> None:
        # Arrange
        organization = Organization.objects.all()[0]
        event = Event.objects.create(slug="test-event", host=organization, administrator=organization)
        recruitment = InstructorRecruitment.objects.create(event=event, notes="Test notes")
        person = Person.objects.create(email="test@example.org")
        signup = InstructorRecruitmentSignup.objects.create(recruitment=recruitment, person=person)
        request = RequestFactory().get("/")
        signal = instructor_signs_up_for_workshop_signal.signal_name

        # Act
        instructor_signs_up_for_workshop_signal.send(
            sender=signup,
            request=request,
            person_id=signup.person.pk,
            event_id=signup.recruitment.event.pk,
            instructor_recruitment_id=signup.recruitment.pk,
            instructor_recruitment_signup_id=signup.pk,
        )

        # Assert
        mock_messages_missing_template.assert_called_once_with(request, signal)


class TestInstructorSignsUpForWorkshopReceiverIntegration(TestBase):
    @override_settings(
        FLAGS={
            "INSTRUCTOR_RECRUITMENT": [("boolean", True)],
            "EMAIL_MODULE": [("boolean", True)],
        }
    )
    @patch("django.contrib.messages.views.messages")
    @patch("emails.actions.base_action.messages_action_scheduled")
    def test_integration(
        self,
        mock_messages_action_scheduled: MagicMock,
        mock_contrib_messages_views: MagicMock,
    ) -> None:
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create_user(
            username="test_test",
            personal="Test",
            family="User",
            email="test@user.com",
            password="test",
        )
        consent_to_all_required_consents(person)
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
        event = Event.objects.create(slug="test-event", host=host, start=date(2023, 7, 22), end=date(2023, 7, 23))
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=instructor_signs_up_for_workshop_signal.signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ person.personal }}",
            body="Hello, {{ person.personal }}! Nice to meet **you**.",
        )

        url = reverse("signup-for-recruitment", kwargs={"recruitment_pk": recruitment.pk})
        payload = {"user_notes": "Test notes"}
        self.client.login(username="test_test", password="test")

        # Act
        rv = self.client.post(url, payload)

        # Assert
        self.assertEqual(rv.status_code, 302)
        ScheduledEmail.objects.get(template=template)
