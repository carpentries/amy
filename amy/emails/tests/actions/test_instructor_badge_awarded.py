from datetime import UTC, datetime, timedelta
from unittest import mock

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.actions import instructor_badge_awarded_receiver
from emails.models import EmailTemplate, ScheduledEmail
from emails.signals import instructor_badge_awarded_signal
from workshops.models import Award, Badge, Person
from workshops.tests.base import TestBase


class TestInstructorBadgeAwardedReceiver(TestCase):
    @mock.patch("workshops.utils.feature_flags.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            instructor_badge_awarded_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping "
                "instructor_badge_awarded_receiver"
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
    def test_action_triggered(self) -> None:
        # Arrange
        badge = Badge.objects.create(name="instructor")
        person = Person.objects.create()
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
        with mock.patch(
            "emails.actions.messages_action_scheduled"
        ) as mock_messages_action_scheduled:
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
    @mock.patch("emails.actions.messages_action_scheduled")
    @mock.patch("emails.actions.immediate_action")
    def test_email_scheduled(
        self,
        mock_immediate_action: mock.MagicMock,
        mock_messages_action_scheduled: mock.MagicMock,
    ) -> None:
        # Arrange
        NOW = datetime(2023, 6, 1, 10, 0, 0, tzinfo=UTC)
        mock_immediate_action.return_value = NOW + timedelta(hours=1)
        badge = Badge.objects.create(name="instructor")
        person = Person.objects.create()
        award = Award.objects.create(badge=badge, person=person)
        request = RequestFactory().get("/")
        signal = instructor_badge_awarded_signal.signal_name
        context = {
            "person": person,
            "award": award,
        }
        scheduled_at = NOW + timedelta(hours=1)

        # Act
        with mock.patch(
            "emails.actions.EmailController.schedule_email"
        ) as mock_schedule_email:
            instructor_badge_awarded_signal.send(
                sender=award,
                request=request,
                person_id=person.pk,
                award_id=award.pk,
            )

        # Assert
        mock_schedule_email.assert_called_once_with(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[person.email],
            generic_relation_obj=award,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @mock.patch("emails.actions.messages_missing_template")
    def test_missing_template(
        self, mock_messages_missing_template: mock.MagicMock
    ) -> None:
        # Arrange
        badge = Badge.objects.create(name="instructor")
        person = Person.objects.create()
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
    def test_integration(self) -> None:
        # Arrange
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
            airport=self.airport_0_0,
            github="purdy_kelsi",
            twitter="purdy_kelsi",
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
