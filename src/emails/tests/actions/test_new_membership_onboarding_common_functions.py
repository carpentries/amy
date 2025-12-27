from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase

from src.emails.actions.new_membership_onboarding import (
    get_context,
    get_generic_relation_object,
    get_recipients,
    get_scheduled_at,
)
from src.emails.types import NewMembershipOnboardingContext
from src.fiscal.models import MembershipPersonRole, MembershipTask
from src.workshops.models import Membership, Person


class TestNewMembershipOnboardingCommonFunctions(TestCase):
    def setUpMembershipTasks(self, membership: Membership, person1: Person, person2: Person) -> list[MembershipTask]:
        role1 = MembershipPersonRole.objects.create(name="billing_contact")
        role2 = MembershipPersonRole.objects.create(name="programmatic_contact")

        tasks = MembershipTask.objects.bulk_create(
            [
                MembershipTask(membership=membership, person=person1, role=role1),
                MembershipTask(membership=membership, person=person2, role=role2),
            ]
        )
        return tasks

    def setUpContext(self, membership: Membership) -> NewMembershipOnboardingContext:
        return {
            "membership": membership,
        }

    @patch("src.emails.actions.new_membership_onboarding.immediate_action")
    def test_get_scheduled_at__immediately(self, mock_immediate_action: MagicMock) -> None:
        # Arrange
        membership_start_date = date(2022, 1, 1)
        membership = Membership(
            name="Test Membership",
            variant="gold",
            agreement_start=membership_start_date,
            agreement_end=membership_start_date,
            contribution_type="financial",
        )
        mock_immediate_action.return_value = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Act
        scheduled_at = get_scheduled_at(membership=membership)

        # Assert
        self.assertEqual(scheduled_at, datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC))

    @patch("src.emails.utils.datetime", wraps=datetime)
    @patch("src.emails.actions.new_membership_onboarding.immediate_action")
    def test_get_scheduled_at__one_month_before_arrangement_start(
        self, mock_immediate_action: MagicMock, mock_datetime: MagicMock
    ) -> None:
        # Arrange
        membership_start_date = date(2023, 6, 1)
        membership = Membership(
            name="Test Membership",
            variant="gold",
            agreement_start=membership_start_date,
            agreement_end=membership_start_date,
            contribution_type="financial",
        )
        mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_immediate_action.return_value = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)

        # Act
        scheduled_at = get_scheduled_at(membership=membership)

        # Assert
        self.assertEqual(scheduled_at, datetime(2023, 5, 2, 12, 0, 0, tzinfo=UTC))

    def test_get_context(self) -> None:
        # Arrange
        membership_start_date = date(2023, 1, 1)
        membership = Membership(
            name="Test Membership",
            variant="gold",
            agreement_start=membership_start_date,
            agreement_end=membership_start_date,
            contribution_type="financial",
        )

        # Act
        context = get_context(membership=membership)

        # Assert
        self.assertEqual(
            context,
            {
                "membership": membership,
            },
        )

    def test_get_generic_relation_object(self) -> None:
        # Arrange
        membership_start_date = date(2023, 1, 1)
        membership = Membership(
            name="Test Membership",
            variant="gold",
            agreement_start=membership_start_date,
            agreement_end=membership_start_date,
            contribution_type="financial",
        )

        # Act
        obj = get_generic_relation_object(
            context=self.setUpContext(membership),
            membership=membership,
        )

        # Assert
        self.assertEqual(obj, membership)

    def test_get_recipients(self) -> None:
        # Arrange
        membership_start_date = date(2023, 1, 1)
        membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            agreement_start=membership_start_date,
            agreement_end=membership_start_date,
            contribution_type="financial",
        )
        person1 = Person.objects.create(username="test1", email="test1@example.org")
        person2 = Person.objects.create(username="test2", email="test2@example.org")
        self.setUpMembershipTasks(membership, person1, person2)

        # Act
        obj = get_recipients(
            context=self.setUpContext(membership),
            membership=membership,
        )

        # Assert
        self.assertEqual(obj, ["test1@example.org", "test2@example.org"])

    def test_get_recipients__no_email(self) -> None:
        # Arrange
        membership_start_date = date(2023, 1, 1)
        membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            agreement_start=membership_start_date,
            agreement_end=membership_start_date,
            contribution_type="financial",
        )
        # self.setUpMembershipTasks(membership)  # no tasks for this membership

        # Act
        obj = get_recipients(
            context=self.setUpContext(membership),
            membership=membership,
        )

        # Assert
        self.assertEqual(obj, [])
