from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.contrib import messages
from django.test import RequestFactory, TestCase, override_settings

from src.emails.actions.membership_quarterly_emails import (
    get_context,
    get_context_json,
    get_generic_relation_object,
    get_recipients,
    get_recipients_context_json,
    get_scheduled_at,
    run_membership_quarterly_email_strategy,
    update_context_json_and_to_header_json,
)
from src.emails.models import EmailTemplate, ScheduledEmail
from src.emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from src.emails.signals import (
    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
)
from src.emails.types import MembershipQuarterlyContext, StrategyEnum
from src.emails.utils import api_model_url
from src.fiscal.models import MembershipPersonRole, MembershipTask
from src.workshops.models import Event, Membership, Organization, Person, Role, Task


class TestMembershipQuarterlyEmailsCommonFunctions(TestCase):
    def set_up_membership(self) -> Membership:
        return Membership.objects.create(
            name="Test Membership",
            variant="gold",
            agreement_start=date(2022, 1, 1),
            agreement_end=date(2023, 1, 1),
            contribution_type="financial",
        )

    def set_up_membership_task(self, membership: Membership, person: Person) -> MembershipTask:
        billing_contact_role, _ = MembershipPersonRole.objects.get_or_create(name="billing_contact")
        return MembershipTask.objects.create(
            membership=membership,
            person=person,
            role=billing_contact_role,
        )

    def set_up_event_for_membership(self, membership: Membership) -> Event:
        return Event.objects.create(
            slug="test-event",
            membership=membership,
            host=Organization.objects.all()[0],
        )

    def set_up_learner_task(self, membership: Membership, person: Person, event: Event) -> Task:
        learner, _ = Role.objects.get_or_create(name="learner")
        return Task.objects.create(
            event=event,
            seat_membership=membership,
            person=person,
            role=learner,
        )

    def set_up_email_template(self, signal_name: str) -> EmailTemplate:
        return EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal_name,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )

    @patch("src.emails.utils.datetime", wraps=datetime)
    def test_get_scheduled_at__3_months(self, mock_datetime: MagicMock) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        membership = self.set_up_membership()
        signal_name = MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME
        # Act
        result = get_scheduled_at(signal_name, membership=membership)
        # Assert
        self.assertEqual(result, datetime(2022, 4, 1, tzinfo=UTC))

    @patch("src.emails.utils.datetime", wraps=datetime)
    def test_get_scheduled_at__6_months(self, mock_datetime: MagicMock) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        membership = self.set_up_membership()
        signal_name = MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME
        # Act
        result = get_scheduled_at(signal_name, membership=membership)
        # Assert
        self.assertEqual(result, datetime(2022, 6, 30, tzinfo=UTC))

    @patch("src.emails.utils.datetime", wraps=datetime)
    def test_get_scheduled_at__9_months(self, mock_datetime: MagicMock) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        membership = self.set_up_membership()
        signal_name = MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME
        # Act
        result = get_scheduled_at(signal_name, membership=membership)
        # Assert
        self.assertEqual(result, datetime(2022, 10, 3, tzinfo=UTC))

    def test_get_context(self) -> None:
        # Arrange
        membership = self.set_up_membership()
        person = Person.objects.create(username="test1", email="test1@example.com")
        self.set_up_membership_task(membership, person)
        event = self.set_up_event_for_membership(membership)
        task = self.set_up_learner_task(membership, person, event)
        # Act
        result = get_context(membership=membership)
        # Assert
        self.assertEqual(
            result,
            {
                "membership": membership,
                "member_contacts": [person],
                "events": [event],
                "trainee_tasks": [task],
                "trainees": [person],
            },
        )

    def test_get_context_json(self) -> None:
        # Arrange
        membership = self.set_up_membership()
        person = Person.objects.create(username="test1", email="test1@example.com")
        self.set_up_membership_task(membership, person)
        event = self.set_up_event_for_membership(membership)
        task = self.set_up_learner_task(membership, person, event)
        context: MembershipQuarterlyContext = {
            "membership": membership,
            "member_contacts": [person],
            "events": [event],
            "trainee_tasks": [task],
            "trainees": [person],
        }
        # Act
        result = get_context_json(context)
        # Assert
        self.assertEqual(
            result,
            ContextModel(
                {
                    "membership": api_model_url("membership", membership.pk),
                    "member_contacts": [api_model_url("person", person.pk)],
                    "events": [api_model_url("event", event.pk)],
                    "trainee_tasks": [api_model_url("task", task.pk)],
                    "trainees": [api_model_url("person", person.pk)],
                }
            ),
        )

    def test_get_generic_relation_object(self) -> None:
        # Arrange
        membership = self.set_up_membership()
        person = Person.objects.create(username="test1", email="test1@example.com")
        self.set_up_membership_task(membership, person)
        event = self.set_up_event_for_membership(membership)
        task = self.set_up_learner_task(membership, person, event)
        context: MembershipQuarterlyContext = {
            "membership": membership,
            "member_contacts": [person],
            "events": [event],
            "trainee_tasks": [task],
            "trainees": [person],
        }
        # Act
        result = get_generic_relation_object(context, membership=membership)
        # Assert
        self.assertEqual(result, membership)

    def test_get_recipients(self) -> None:
        # Arrange
        membership = self.set_up_membership()
        person1 = Person.objects.create(username="test1", email="test1@example.com")
        person2 = Person.objects.create(username="test2")
        self.set_up_membership_task(membership, person1)
        self.set_up_membership_task(membership, person2)
        event = self.set_up_event_for_membership(membership)
        task = self.set_up_learner_task(membership, person1, event)
        context: MembershipQuarterlyContext = {
            "membership": membership,
            "member_contacts": [person1, person2],
            "events": [event],
            "trainee_tasks": [task],
            "trainees": [person1],
        }
        # Act
        result = get_recipients(context, membership=membership)
        # Assert
        self.assertEqual(result, ["test1@example.com"])

    def test_get_recipients_context_json(self) -> None:
        # Arrange
        membership = self.set_up_membership()
        person1 = Person.objects.create(username="test1", email="test1@example.com")
        person2 = Person.objects.create(username="test2")
        self.set_up_membership_task(membership, person1)
        self.set_up_membership_task(membership, person2)
        event = self.set_up_event_for_membership(membership)
        task = self.set_up_learner_task(membership, person1, event)
        context: MembershipQuarterlyContext = {
            "membership": membership,
            "member_contacts": [person1, person2],
            "events": [event],
            "trainee_tasks": [task],
            "trainees": [person1],
        }
        # Act
        result = get_recipients_context_json(context, membership=membership)
        # Assert
        self.assertEqual(
            result,
            ToHeaderModel(
                [
                    SinglePropertyLinkModel(
                        api_uri=api_model_url("person", person1.pk),
                        property="email",
                    ),
                ]
            ),
        )

    @override_settings(MESSAGE_STORAGE="django.contrib.messages.storage.cookie.CookieStorage")
    def test_update_context_json_and_to_header_json(self) -> None:
        # Arrange
        signal_name = MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME
        request = RequestFactory().get("/")
        request._messages = messages.storage.default_storage(request)  # type: ignore
        membership = self.set_up_membership()
        person1 = Person.objects.create(username="test1", email="test1@example.com")
        self.set_up_membership_task(membership, person1)
        template = self.set_up_email_template(signal_name)
        run_membership_quarterly_email_strategy(signal_name, StrategyEnum.CREATE, request, membership)
        email = ScheduledEmail.objects.get(template=template)

        # Act
        person2 = Person.objects.create(username="test2", email="test2@example.com")
        self.set_up_membership_task(membership, person2)
        event = self.set_up_event_for_membership(membership)
        task = self.set_up_learner_task(membership, person1, event)
        updated_email = update_context_json_and_to_header_json(signal_name, request, membership)

        # Assert
        assert updated_email is not None
        self.assertEqual(email.pk, updated_email.pk)
        self.assertEqual(
            set(updated_email.to_header),
            set(email.to_header + [person2.email]),
        )
        # `to_header_context_json` is a list with dicts, so to compare it without considering the order,
        # `set(tuple(d.items()) for d in list)` had to be used.
        self.assertEqual(
            set(tuple(d.items()) for d in updated_email.to_header_context_json),
            set(
                tuple(d.items())
                for d in (
                    email.to_header_context_json
                    + [{"api_uri": api_model_url("person", person2.pk), "property": "email"}]
                )
            ),
        )
        self.assertNotEqual(updated_email.context_json, email.context_json)
        self.assertEqual(
            set(updated_email.context_json["member_contacts"]),
            set([api_model_url("person", person1.pk), api_model_url("person", person2.pk)]),
        )
        self.assertEqual(
            updated_email.context_json["events"],
            [api_model_url("event", event.pk)],
        )
        self.assertEqual(
            updated_email.context_json["trainees"],
            [api_model_url("person", person1.pk)],
        )
        self.assertEqual(
            updated_email.context_json["trainee_tasks"],
            [api_model_url("task", task.pk)],
        )

    def test_update_context_json_and_to_header_json__email_not_found(self) -> None:
        # Arrange
        signal_name = MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME
        request = RequestFactory().get("/")
        membership = self.set_up_membership()

        # Act
        updated_email = update_context_json_and_to_header_json(signal_name, request, membership)

        # Assert
        self.assertIsNone(updated_email)
