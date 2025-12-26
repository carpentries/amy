import tempfile
from datetime import UTC, date, datetime, timedelta
from unittest.mock import ANY, MagicMock, patch

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from src.emails.actions.instructor_badge_awarded import (
    generate_and_attach_certificate_pdf,
    generate_pdf,
    instructor_badge_awarded_receiver,
    read_binary_file_and_replace_values,
)
from src.emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from src.emails.schemas import ContextModel, ToHeaderModel
from src.emails.signals import (
    INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
    instructor_badge_awarded_signal,
)
from src.emails.utils import api_model_url, scalar_value_url
from src.workshops.models import Award, Badge, Person
from src.workshops.tests.base import TestBase


class TestInstructorBadgeAwardedReceiver(TestCase):
    @patch("src.emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            instructor_badge_awarded_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping instructor_badge_awarded"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = instructor_badge_awarded_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        instructor_badge_awarded_signal.connect(instructor_badge_awarded_receiver)
        new_receivers = instructor_badge_awarded_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.instructor_badge_awarded.EmailController.add_attachment")
    def test_action_triggered(self, mock_add_attachment: MagicMock) -> None:
        # Arrange
        mock_add_attachment.return_value = None
        badge = Badge.objects.create(name="instructor")
        person = Person.objects.create(email="test@example.org")
        award = Award.objects.create(badge=badge, person=person)
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=instructor_badge_awarded_signal.signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        # Act
        with patch("src.emails.actions.base_action.messages_action_scheduled") as mock_messages_action_scheduled:
            instructor_badge_awarded_signal.send(
                sender=award,
                request=request,
                person_id=person.pk,
                award_id=award.pk,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_scheduled.assert_called_once_with(
            request,
            instructor_badge_awarded_signal.signal_name,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_action_scheduled")
    @patch("src.emails.actions.instructor_badge_awarded.immediate_action")
    def test_email_scheduled(
        self,
        mock_immediate_action: MagicMock,
        mock_messages_action_scheduled: MagicMock,
    ) -> None:
        # Arrange
        NOW = datetime(2023, 6, 1, 10, 0, 0, tzinfo=UTC)
        mock_immediate_action.return_value = NOW + timedelta(hours=1)
        badge = Badge.objects.create(name="instructor")
        person = Person.objects.create(email="test@example.org")
        award = Award.objects.create(badge=badge, person=person)
        request = RequestFactory().get("/")
        signal = instructor_badge_awarded_signal.signal_name
        scheduled_at = NOW + timedelta(hours=1)

        # Act
        with patch("src.emails.actions.base_action.EmailController.schedule_email") as mock_schedule_email:
            instructor_badge_awarded_signal.send(
                sender=award,
                request=request,
                person_id=person.pk,
                award_id=award.pk,
            )

        # Assert
        mock_schedule_email.assert_called_once_with(
            signal=signal,
            context_json=ContextModel(
                {
                    "person": api_model_url("person", person.pk),
                    "award": api_model_url("award", award.pk),
                    "award_id": scalar_value_url("int", str(award.pk)),
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
            generic_relation_obj=award,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_missing_recipients")
    def test_missing_recipients(self, mock_messages_missing_recipients: MagicMock) -> None:
        # Arrange
        badge = Badge.objects.create(name="instructor")
        person = Person.objects.create()  # no email will cause missing recipients error
        award = Award.objects.create(badge=badge, person=person)
        request = RequestFactory().get("/")
        signal = instructor_badge_awarded_signal.signal_name

        # Act
        instructor_badge_awarded_signal.send(
            sender=award,
            request=request,
            person_id=person.pk,
            award_id=award.pk,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.base_action.messages_missing_template")
    def test_missing_template(self, mock_messages_missing_template: MagicMock) -> None:
        # Arrange
        badge = Badge.objects.create(name="instructor")
        person = Person.objects.create(email="test@example.org")
        award = Award.objects.create(badge=badge, person=person)
        request = RequestFactory().get("/")
        signal = instructor_badge_awarded_signal.signal_name

        # Act
        instructor_badge_awarded_signal.send(
            sender=award,
            request=request,
            person_id=person.pk,
            award_id=award.pk,
        )

        # Assert
        mock_messages_missing_template.assert_called_once_with(request, signal)


class TestInstructorBadgeAwardedReceiverIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("src.emails.actions.instructor_badge_awarded.EmailController.add_attachment")
    def test_integration(self, mock_add_attachment: MagicMock) -> None:
        # Arrange
        mock_add_attachment.return_value = None
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
            mastodon="https://mastodon.social/@sdfgh",
            url="http://kelsipurdy.com/",
            affiliation="University of Arizona",
            occupation="TA at Biology Department",
            orcid="0000-0000-0000",
            is_active=True,
        )
        payload = {
            "award-person": person.pk,
            "award-badge": badge.pk,
            "award-awarded": "2023-07-23",
        }
        url = reverse("award_add")

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=instructor_badge_awarded_signal.signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ person.personal }}",
            body="Hello, {{ person.personal }}! Nice to meet **you**.",
        )

        # Act
        rv = self.client.post(url, data=payload)

        # Assert
        self.assertEqual(rv.status_code, 302)
        ScheduledEmail.objects.get(template=template)


class TestInstructorBadgeAwardedCertificates(TestCase):
    def test_read_binary_file_and_replace_values(self) -> None:
        # Arrange
        with tempfile.NamedTemporaryFile(delete_on_close=False) as fp:
            fp.write(b"<h1>Hello, {{personal}} {{family}}</h1>")
            fp.close()

            # Act
            result = read_binary_file_and_replace_values(
                fp.name,
                {
                    b"{{personal}}": b"John",
                    b"{{family}}": b"Smith",
                },
            )

        # Assert
        self.assertEqual(result, b"<h1>Hello, John Smith</h1>")

    @patch("src.emails.actions.instructor_badge_awarded.cairosvg.svg2pdf")
    def test_generate_certificate(self, mock_svg2pdf: MagicMock) -> None:
        # Arrange
        svg_file = b"Test file"
        # Act
        generate_pdf(svg_file)
        # Assert
        mock_svg2pdf.assert_called_once_with(svg_file, write_to=ANY, dpi=90)

    @patch("src.emails.actions.instructor_badge_awarded.logger")
    def test_generate_and_attach_certificate_pdf__no_sender(self, mock_logger: MagicMock) -> None:
        # Arrange
        sender = None
        # Act
        generate_and_attach_certificate_pdf(sender)
        # Assert - No action happens
        mock_logger.error.assert_called_once_with(
            "Failed to generate and attach certificate: sender is not a ScheduledEmail (it's None)"
        )

    @patch("src.emails.actions.instructor_badge_awarded.logger")
    def test_generate_and_attach_certificate_pdf__generic_relation_not_award(self, mock_logger: MagicMock) -> None:
        # Arrange
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        sender = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=None,
        )
        # Act
        generate_and_attach_certificate_pdf(sender)
        # Assert - No action happens
        mock_logger.error.assert_called_once_with(
            "Failed to generate and attach certificate: related object is not an Award (it's None)"
        )

    @patch("src.emails.actions.instructor_badge_awarded.EmailController.add_attachment")
    def test_generate_and_attach_certificate_pdf(self, mock_add_attachment: MagicMock) -> None:
        # Arrange
        self.badge = Badge.objects.create(name="instructor")
        self.person = Person.objects.create(personal="John", family="Smith", email="test@example.org")
        award = Award.objects.create(badge=self.badge, person=self.person, awarded=date(2025, 3, 10))
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        sender = ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=ScheduledEmailStatus.SCHEDULED,
            generic_relation=award,
        )
        # Act
        generate_and_attach_certificate_pdf(sender)
        # Assert
        mock_add_attachment.assert_called_once_with(sender, filename="certificate.pdf", content=ANY)
