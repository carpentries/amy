from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.test import RequestFactory, TestCase

from emails.actions.membership_quarterly_emails import (
    get_context,
    get_context_json,
    get_generic_relation_object,
    get_recipients,
    get_recipients_context_json,
    get_scheduled_at,
)
from emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from emails.signals import (
    MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
)
from emails.types import MembershipQuarterlyContext
from emails.utils import api_model_url
from fiscal.models import MembershipPersonRole, MembershipTask
from workshops.models import Membership, Person


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

    @patch("emails.utils.datetime", wraps=datetime)
    def test_get_scheduled_at__3_months(self, mock_datetime: MagicMock) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        request = RequestFactory().get("/")
        membership = self.set_up_membership()
        signal_name = MEMBERSHIP_QUARTERLY_3_MONTHS_SIGNAL_NAME
        # Act
        result = get_scheduled_at(signal_name, request=request, membership=membership)
        # Assert
        self.assertEqual(result, datetime(2022, 4, 1, tzinfo=UTC))

    @patch("emails.utils.datetime", wraps=datetime)
    def test_get_scheduled_at__6_months(self, mock_datetime: MagicMock) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        request = RequestFactory().get("/")
        membership = self.set_up_membership()
        signal_name = MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME
        # Act
        result = get_scheduled_at(signal_name, request=request, membership=membership)
        # Assert
        self.assertEqual(result, datetime(2022, 6, 30, tzinfo=UTC))

    @patch("emails.utils.datetime", wraps=datetime)
    def test_get_scheduled_at__9_months(self, mock_datetime: MagicMock) -> None:
        # Arrange
        mock_datetime.now.return_value = datetime(2023, 1, 1, 0, 0, 0, tzinfo=UTC)
        request = RequestFactory().get("/")
        membership = self.set_up_membership()
        signal_name = MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME
        # Act
        result = get_scheduled_at(signal_name, request=request, membership=membership)
        # Assert
        self.assertEqual(result, datetime(2022, 10, 3, tzinfo=UTC))

    def test_get_context(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        membership = self.set_up_membership()
        # Act
        result = get_context(request=request, membership=membership)
        # Assert
        self.assertEqual(result, {"membership": membership})

    def test_get_context_json(self) -> None:
        # Arrange
        membership = self.set_up_membership()
        context: MembershipQuarterlyContext = {"membership": membership}
        # Act
        result = get_context_json(context)
        # Assert
        self.assertEqual(result, ContextModel({"membership": api_model_url("membership", membership.pk)}))

    def test_get_generic_relation_object(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        membership = self.set_up_membership()
        context: MembershipQuarterlyContext = {"membership": membership}
        # Act
        result = get_generic_relation_object(context, request=request, membership=membership)
        # Assert
        self.assertEqual(result, membership)

    def test_get_recipients(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        membership = self.set_up_membership()
        person1 = Person.objects.create(username="test1", email="test1@example.com")
        person2 = Person.objects.create(username="test2")
        self.set_up_membership_task(membership, person1)
        self.set_up_membership_task(membership, person2)
        context: MembershipQuarterlyContext = {"membership": membership}
        # Act
        result = get_recipients(context, request=request, membership=membership)
        # Assert
        self.assertEqual(result, ["test1@example.com"])

    def test_get_recipients_context_json(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        membership = self.set_up_membership()
        person1 = Person.objects.create(username="test1", email="test1@example.com")
        person2 = Person.objects.create(username="test2")
        self.set_up_membership_task(membership, person1)
        self.set_up_membership_task(membership, person2)
        context: MembershipQuarterlyContext = {"membership": membership}
        # Act
        result = get_recipients_context_json(context, request=request, membership=membership)
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
