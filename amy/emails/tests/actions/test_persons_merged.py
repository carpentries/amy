from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch
from urllib.parse import urlencode

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.actions import persons_merged_receiver
from emails.models import EmailTemplate, ScheduledEmail
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import persons_merged_signal
from emails.utils import api_model_url
from workshops.models import Person
from workshops.tests.base import TestBase


class TestPersonsMergedReceiver(TestCase):
    @patch("emails.actions.base_action.logger")
    def test_disabled_when_no_feature_flag(self, mock_logger: MagicMock) -> None:
        # Arrange
        request = RequestFactory().get("/")
        with self.settings(FLAGS={"EMAIL_MODULE": [("boolean", False)]}):
            # Act
            persons_merged_receiver(None, request=request)
            # Assert
            mock_logger.debug.assert_called_once_with(
                "EMAIL_MODULE feature flag not set, skipping persons_merged"
            )

    def test_receiver_connected_to_signal(self) -> None:
        # Arrange
        original_receivers = persons_merged_signal.receivers[:]

        # Act
        # attempt to connect the receiver
        persons_merged_signal.connect(persons_merged_receiver)
        new_receivers = persons_merged_signal.receivers[:]

        # Assert
        # the same receiver list means this receiver has already been connected
        self.assertEqual(original_receivers, new_receivers)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_action_triggered(self) -> None:
        # Arrange
        person = Person.objects.create(email="test@example.org")
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=persons_merged_signal.signal_name,
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
            persons_merged_signal.send(
                sender=person,
                request=request,
                person_a_id=person.pk,
                person_b_id=person.pk,
                selected_person_id=person.pk,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages_action_scheduled.assert_called_once_with(
            request,
            persons_merged_signal.signal_name,
            scheduled_email,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_action_scheduled")
    @patch("emails.actions.persons_merged.immediate_action")
    def test_email_scheduled(
        self,
        mock_immediate_action: MagicMock,
        mock_messages_action_scheduled: MagicMock,
    ) -> None:
        # Arrange
        NOW = datetime(2023, 6, 1, 10, 0, 0, tzinfo=UTC)
        mock_immediate_action.return_value = NOW + timedelta(hours=1)
        person = Person.objects.create(email="test@example.org")
        request = RequestFactory().get("/")
        signal = persons_merged_signal.signal_name
        scheduled_at = NOW + timedelta(hours=1)

        # Act
        with patch(
            "emails.actions.base_action.EmailController.schedule_email"
        ) as mock_schedule_email:
            persons_merged_signal.send(
                sender=person,
                request=request,
                person_a_id=person.pk,
                person_b_id=person.pk,
                selected_person_id=person.pk,
            )

        # Assert
        mock_schedule_email.assert_called_once_with(
            signal=signal,
            context_json=ContextModel({"person": api_model_url("person", person.pk)}),
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
            generic_relation_obj=person,
            author=None,
        )

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_missing_recipients")
    def test_missing_recipients(
        self, mock_messages_missing_recipients: MagicMock
    ) -> None:
        # Arrange
        person = Person.objects.create()  # no email will cause missing recipients error
        request = RequestFactory().get("/")
        signal = persons_merged_signal.signal_name

        # Act
        persons_merged_signal.send(
            sender=person,
            request=request,
            person_a_id=person.pk,
            person_b_id=person.pk,
            selected_person_id=person.pk,
        )

        # Assert
        mock_messages_missing_recipients.assert_called_once_with(request, signal)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @patch("emails.actions.base_action.messages_missing_template")
    def test_missing_template(self, mock_messages_missing_template: MagicMock) -> None:
        # Arrange
        person = Person.objects.create(email="test@example.org")
        request = RequestFactory().get("/")
        signal = persons_merged_signal.signal_name

        # Act
        persons_merged_signal.send(
            sender=person,
            request=request,
            person_a_id=person.pk,
            person_b_id=person.pk,
            selected_person_id=person.pk,
        )

        # Assert
        mock_messages_missing_template.assert_called_once_with(request, signal)


class TestPersonsMergedSignalReceiverIntegration(TestBase):
    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    def test_integration(self) -> None:
        # Arrange
        self._setUpUsersAndLogin()
        person_a = Person.objects.create(
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
        person_b = Person.objects.create(
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
        strategy = {
            "person_a": person_a.pk,
            "person_b": person_b.pk,
            "id": "obj_b",
            "username": "obj_a",
            "personal": "obj_b",
            "middle": "obj_a",
            "family": "obj_a",
            "email": "obj_b",
            "secondary_email": "obj_b",
            "gender": "obj_b",
            "gender_other": "obj_b",
            "airport": "obj_a",
            "github": "obj_b",
            "twitter": "obj_a",
            "bluesky": "obj_a",
            "url": "obj_b",
            "affiliation": "obj_b",
            "occupation": "obj_a",
            "orcid": "obj_b",
            "award_set": "obj_a",
            "qualification_set": "obj_b",
            "domains": "combine",
            "languages": "combine",
            "task_set": "obj_b",
            "is_active": "obj_a",
            "trainingprogress_set": "obj_b",
            "comment_comments": "obj_b",  # made by this person
            "comments": "obj_b",  # regarding this person
            "consent_set": "most_recent",
        }
        base_url = reverse("persons_merge")
        query = urlencode({"person_a": person_a.pk, "person_b": person_b.pk})
        url = "{}?{}".format(base_url, query)

        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=persons_merged_signal.signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ person.personal }}",
            body="Hello, {{ person.personal }}! Nice to meet **you**.",
        )

        # Act
        rv = self.client.post(url, data=strategy)

        # Assert
        self.assertEqual(rv.status_code, 302)
        person_b.refresh_from_db()
        with self.assertRaises(Person.DoesNotExist):
            person_a.refresh_from_db()
        ScheduledEmail.objects.get(template=template)
