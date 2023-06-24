from datetime import UTC, datetime, timedelta
from unittest import mock
from urllib.parse import urlencode
import weakref

from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from emails.models import EmailTemplate, ScheduledEmail
from emails.signals import persons_merged_signal
from workshops.models import Person
from workshops.tests.base import TestBase


class TestPersonsMergedReceived(TestCase):
    def test_signal_received(self) -> None:
        # Arrange
        person = Person.objects.create()
        request = RequestFactory().get("/")
        mock_action = mock.MagicMock()
        _copied_receivers = persons_merged_signal.receivers[:]

        # This hack replaces weakref to "emails.actions.persons_merged_receiver" with
        # a mock. Otherwise mocking doesn't work, as after dereferencing the weakref
        # the actual function is called.
        persons_merged_signal.receivers[0] = (
            persons_merged_signal.receivers[0][0],
            weakref.ref(mock_action),
        )

        # Act
        persons_merged_signal.send(
            sender=person,
            request=request,
            person_a_id=person.id,
            person_b_id=person.id,
            selected_person_id=person.id,
        )

        # Assert
        mock_action.assert_called_once_with(
            signal=mock.ANY,
            sender=person,
            request=request,
            person_a_id=person.id,
            person_b_id=person.id,
            selected_person_id=person.id,
        )

        # Finally
        persons_merged_signal.receivers = _copied_receivers[:]

    @override_settings(EMAIL_MODULE_ENABLED=True)
    def test_action_triggered(self) -> None:
        # Arrange
        person = Person.objects.create()
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal="persons_merged",
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        request = RequestFactory().get("/")

        # Act
        with mock.patch("emails.actions.messages") as mock_messages:
            persons_merged_signal.send(
                sender=person,
                request=request,
                person_a_id=person.id,
                person_b_id=person.id,
                selected_person_id=person.id,
            )

        # Assert
        scheduled_email = ScheduledEmail.objects.get(template=template)
        mock_messages.info.assert_called_once_with(
            request, f"Action was scheduled: {scheduled_email.get_absolute_url()}."
        )

    @override_settings(EMAIL_MODULE_ENABLED=True)
    @mock.patch("emails.actions.messages")
    @mock.patch("emails.actions.timezone")
    def test_email_scheduled(
        self, mock_timezone: mock.MagicMock, mock_messages: mock.MagicMock
    ) -> None:
        # Arrange
        NOW = datetime(2023, 6, 1, 10, 0, 0, tzinfo=UTC)
        mock_timezone.now.return_value = NOW
        person = Person.objects.create()
        request = RequestFactory().get("/")
        signal = "persons_merged"
        context = {"person": person}
        scheduled_at = NOW + timedelta(hours=1)

        # Act
        with mock.patch(
            "emails.actions.EmailController.schedule_email"
        ) as mock_schedule_email:
            persons_merged_signal.send(
                sender=person,
                request=request,
                person_a_id=person.id,
                person_b_id=person.id,
                selected_person_id=person.id,
            )

        # Assert
        mock_schedule_email.assert_called_once_with(
            signal=signal,
            context=context,
            scheduled_at=scheduled_at,
            to_header=[person.email],
        )

    @override_settings(EMAIL_MODULE_ENABLED=True)
    @mock.patch("emails.actions.messages")
    def test_missing_template(self, mock_messages: mock.MagicMock) -> None:
        # Arrange
        person = Person.objects.create()
        request = RequestFactory().get("/")
        signal = "persons_merged"

        # Act
        persons_merged_signal.send(
            sender=person,
            request=request,
            person_a_id=person.id,
            person_b_id=person.id,
            selected_person_id=person.id,
        )

        # Assert
        mock_messages.warning.assert_called_once_with(
            request,
            f"Action was not scheduled due to missing template for signal {signal}.",
        )


class TestPersonsMergedSignalReceiverIntegration(TestBase):
    @override_settings(EMAIL_MODULE_ENABLED=True)
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
            signal="persons_merged",
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
