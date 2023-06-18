from datetime import UTC, datetime, timedelta
from unittest import mock
import weakref

from django.test import RequestFactory, TestCase

from emails.models import EmailTemplate, ScheduledEmail
from emails.signals import persons_merged_signal
from workshops.models import Person


class TestPersonsMergedReceived(TestCase):
    def test_signal_received(self) -> None:
        # Arrange
        person = Person.objects.create()
        request = RequestFactory().get("/")
        mock_action = mock.MagicMock()

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
