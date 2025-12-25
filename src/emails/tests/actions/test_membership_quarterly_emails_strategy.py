from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase

from src.emails.actions.exceptions import EmailStrategyException
from src.emails.actions.membership_quarterly_emails import (
    membership_quarterly_email_strategy,
    run_membership_quarterly_email_strategy,
)
from src.emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from src.emails.signals import (
    MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME,
    MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME,
)
from src.emails.types import StrategyEnum
from src.fiscal.models import MembershipPersonRole, MembershipTask
from src.workshops.models import Membership, Person


class TestMembershipQuarterlyEmailsStrategy(TestCase):
    def setUp(self) -> None:
        self.membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            agreement_start=date(2022, 1, 1),
            agreement_end=date(2023, 1, 1),
            contribution_type="financial",
        )
        billing_contact_role, _ = MembershipPersonRole.objects.get_or_create(name="billing_contact")
        person = Person.objects.create()
        MembershipTask.objects.create(
            membership=self.membership,
            person=person,
            role=billing_contact_role,
        )
        self.signal_name = MEMBERSHIP_QUARTERLY_9_MONTHS_SIGNAL_NAME

    def schedule_email(
        self,
        signal: str,
        membership: Membership,
        state: ScheduledEmailStatus = ScheduledEmailStatus.SCHEDULED,
    ) -> ScheduledEmail:
        template = EmailTemplate.objects.create(
            name="Test Email Template",
            signal=signal,
            from_header="workshops@carpentries.org",
            cc_header=["team@carpentries.org"],
            bcc_header=[],
            subject="Greetings {{ name }}",
            body="Hello, {{ name }}! Nice to meet **you**.",
        )
        return ScheduledEmail.objects.create(
            template=template,
            scheduled_at=datetime.now(UTC),
            to_header=[],
            cc_header=[],
            bcc_header=[],
            state=state,
            generic_relation=membership,
        )

    @patch("src.emails.actions.membership_quarterly_emails.ScheduledEmail")
    def test_strategy_finds_correct_scheduled_email_template(self, mock_scheduled_email: MagicMock) -> None:
        # Arrange
        signal_name = "fake-signal"
        ct = ContentType.objects.get_for_model(self.membership)
        # Act
        membership_quarterly_email_strategy(signal_name, self.membership)
        # Assert
        mock_scheduled_email.objects.filter.assert_called_once_with(
            generic_relation_content_type=ct,
            generic_relation_pk=self.membership.pk,
            template__signal=signal_name,
        )

    def test_strategy_create(self) -> None:
        # Act
        result = membership_quarterly_email_strategy(self.signal_name, self.membership)
        # Assert
        self.assertEqual(result, StrategyEnum.CREATE)

    def test_strategy_update(self) -> None:
        # Arrange
        self.schedule_email(self.signal_name, self.membership)
        # Act
        result = membership_quarterly_email_strategy(self.signal_name, self.membership)
        # Assert
        self.assertEqual(result, StrategyEnum.UPDATE)

    def test_strategy_remove__because_no_tasks(self) -> None:
        # Arrange
        self.schedule_email(self.signal_name, self.membership)
        MembershipTask.objects.all().delete()
        # Act
        result = membership_quarterly_email_strategy(self.signal_name, self.membership)
        # Assert
        self.assertEqual(result, StrategyEnum.CANCEL)

    def test_strategy_remove__because_inacceptable_variant(self) -> None:
        # Arrange
        self.schedule_email(self.signal_name, self.membership)
        self.membership.variant = "alacarte"
        self.membership.save()
        # Act
        result = membership_quarterly_email_strategy(self.signal_name, self.membership)
        # Assert
        self.assertEqual(result, StrategyEnum.CANCEL)

    def test_strategy_noop(self) -> None:
        # Act
        membership = Membership()
        result = membership_quarterly_email_strategy(self.signal_name, membership)
        # Assert
        self.assertEqual(result, StrategyEnum.NOOP)


class TestRunMembershipQuarterlyEmailsStrategy(TestCase):
    signal_name = MEMBERSHIP_QUARTERLY_6_MONTHS_SIGNAL_NAME

    def test_strategy_invalid_signal_name(self) -> None:
        # Arrange
        signal_name = "fake-signal"
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        membership = Membership()

        # Act & Assert
        with self.assertRaises(KeyError):
            run_membership_quarterly_email_strategy(signal_name, strategy, request, membership)

    @patch("src.emails.actions.membership_quarterly_emails.membership_quarterly_6_months_signal")
    def test_strategy_calls_create_signal(
        self,
        mock_membership_quarterly_6_months_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CREATE
        request = RequestFactory().get("/")
        membership = Membership()

        # Act
        run_membership_quarterly_email_strategy(self.signal_name, strategy, request, membership)

        # Assert
        mock_membership_quarterly_6_months_signal.send.assert_called_once_with(
            sender=membership,
            request=request,
            membership=membership,
        )

    @patch("src.emails.actions.membership_quarterly_emails.membership_quarterly_6_months_update_signal")
    def test_strategy_calls_update_signal(
        self,
        mock_membership_quarterly_6_months_update_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.UPDATE
        request = RequestFactory().get("/")
        membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            agreement_start=date(2022, 1, 1),
            agreement_end=date(2023, 1, 1),
            contribution_type="financial",
        )

        # Act
        run_membership_quarterly_email_strategy(self.signal_name, strategy, request, membership)

        # Assert
        mock_membership_quarterly_6_months_update_signal.send.assert_called_once_with(
            sender=membership,
            request=request,
            membership=membership,
        )

    @patch("src.emails.actions.membership_quarterly_emails.membership_quarterly_6_months_cancel_signal")
    def test_strategy_calls_cancel_signal(
        self,
        mock_membership_quarterly_6_months_cancel_signal: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.CANCEL
        request = RequestFactory().get("/")
        membership = Membership.objects.create(
            name="Test Membership",
            variant="gold",
            agreement_start=date(2022, 1, 1),
            agreement_end=date(2023, 1, 1),
            contribution_type="financial",
        )

        # Act
        run_membership_quarterly_email_strategy(self.signal_name, strategy, request, membership)

        # Assert
        mock_membership_quarterly_6_months_cancel_signal.send.assert_called_once_with(
            sender=membership,
            request=request,
            membership=membership,
        )

    @patch("src.emails.actions.base_strategy.logger")
    @patch("src.emails.actions.membership_quarterly_emails.membership_quarterly_6_months_signal")
    @patch("src.emails.actions.membership_quarterly_emails.membership_quarterly_6_months_update_signal")
    @patch("src.emails.actions.membership_quarterly_emails.membership_quarterly_6_months_cancel_signal")
    def test_invalid_strategy_no_signal_called(
        self,
        mock_membership_quarterly_6_months_cancel_signal: MagicMock,
        mock_membership_quarterly_6_months_update_signal: MagicMock,
        mock_membership_quarterly_6_months_signal: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        # Arrange
        strategy = StrategyEnum.NOOP
        request = RequestFactory().get("/")
        membership = Membership()

        # Act
        run_membership_quarterly_email_strategy(self.signal_name, strategy, request, membership)

        # Assert
        mock_membership_quarterly_6_months_signal.send.assert_not_called()
        mock_membership_quarterly_6_months_update_signal.send.assert_not_called()
        mock_membership_quarterly_6_months_cancel_signal.send.assert_not_called()
        mock_logger.debug.assert_called_once_with(f"Strategy {strategy} for {membership} is a no-op")

    def test_invalid_strategy(self) -> None:
        # Arrange
        strategy = MagicMock()
        request = RequestFactory().get("/")
        membership = Membership()

        # Act & Assert
        with self.assertRaisesMessage(EmailStrategyException, f"Unknown strategy {strategy}"):
            run_membership_quarterly_email_strategy(self.signal_name, strategy, request, membership)
