from datetime import date, timedelta

from django.test import TestCase

from src.extrequests.tests.test_training_request import create_training_request
from src.extrequests.utils import (
    MemberCodeValidationError,
    accept_training_request_and_match_to_event,
    get_account_benefit_from_partnership,
    get_account_benefit_warnings_after_match,
    get_eventbrite_id_from_url_or_return_input,
    get_membership_or_none_from_code,
    get_membership_warnings_after_match,
    membership_code_valid,
    membership_code_valid_training,
)
from src.fiscal.models import Partnership, PartnershipTier
from src.offering.models import Account, AccountBenefit, Benefit
from src.workshops.models import Event, Membership, Role, Tag, Task
from src.workshops.tests.base import TestBase


class TestMemberCodeValid(TestBase):
    def setUp(self) -> None:
        self._setUpRoles()
        self.date = date.today()

    def setUpMembership(self) -> None:
        self.valid_code = "valid123"
        self.membership = Membership.objects.create(
            name="Alpha Organization",
            variant="bronze",
            agreement_start=date.today() - timedelta(weeks=26),
            agreement_end=date.today() + timedelta(weeks=26),
            contribution_type="financial",
            registration_code=self.valid_code,
            public_instructor_training_seats=1,
            inhouse_instructor_training_seats=1,
        )

    def setUpUsedSeats(self) -> None:
        # set up some prior seat usage
        super().setUp()
        self._setUpTags()
        ttt_event = Event.objects.create(slug="ttt-event", host=self.org_alpha)
        ttt_event.tags.add(Tag.objects.get(name="TTT"))
        learner = Role.objects.get(name="learner")
        self.task_public = Task.objects.create(
            event=ttt_event,
            person=self.spiderman,
            role=learner,
            seat_membership=self.membership,
            seat_public=True,
        )
        self.task_inhouse = Task.objects.create(
            event=ttt_event,
            person=self.blackwidow,
            role=learner,
            seat_membership=self.membership,
            seat_public=False,
        )

    def test_code_valid(self) -> None:
        """Valid member code should pass."""
        # Arrange
        self.setUpMembership()
        code = self.valid_code

        # Act
        result = membership_code_valid(
            code=code,
            date=self.date,
        )

        # Assert
        self.assertTrue(result)

    def test_code_invalid(self) -> None:
        """Invalid member code should not pass."""
        # Arrange
        code = "invalid"

        # Act & Assert
        with self.assertRaises(MemberCodeValidationError, msg='No membership found for code "invalid".'):
            membership_code_valid(
                code=code,
                date=self.date,
            )

    def test__code_inactive_early(self) -> None:
        """Code used before membership start date should not pass."""
        # Arrange
        self.setUpMembership()
        self.membership.agreement_start = date.today() + timedelta(days=91)
        self.membership.save()
        code = self.valid_code
        test_date = date.today() - timedelta(weeks=30)

        # Act & Assert
        with self.assertRaises(
            MemberCodeValidationError,
            msg=(
                "Membership is inactive "
                f"(start {self.membership.agreement_start}, "
                f"end {self.membership.agreement_end})."
            ),
        ):
            membership_code_valid(
                code=code,
                date=test_date,
            )

    def test__code_inactive_late(self) -> None:
        """Code used after membership end date should not pass."""
        # Arrange
        self.setUpMembership()
        self.membership.agreement_start = date.today() + timedelta(days=91)
        self.membership.save()
        code = self.valid_code
        test_date = date.today() + timedelta(weeks=30)

        # Act & Assert
        with self.assertRaises(
            MemberCodeValidationError,
            msg=(
                "Membership is inactive "
                f"(start {self.membership.agreement_start}, "
                f"end {self.membership.agreement_end})."
            ),
        ):
            membership_code_valid(
                code=code,
                date=test_date,
            )

    def test_code_valid_within_grace_before(self) -> None:
        """Code used within a grace period should pass."""
        # Arrange
        self.setUpMembership()
        # we will use a 30-day grace period
        # so set up a membership so that it starts <30 days from today
        self.membership.agreement_start = date.today() + timedelta(days=29)
        self.membership.save()
        code = self.valid_code

        # Act
        result = membership_code_valid(code=code, date=self.date, grace_before=30)

        # Assert
        self.assertTrue(result)

    def test_code_valid_within_grace_after(self) -> None:
        """Code used within a grace period should pass."""
        # Arrange
        self.setUpMembership()
        # we will use a 30-day grace period
        # so set up a membership so that it ends <30 days before today
        self.membership.agreement_end = date.today() - timedelta(days=29)
        self.membership.save()
        code = self.valid_code

        # Act
        result = membership_code_valid(code=code, date=self.date, grace_after=30)

        # Assert
        self.assertTrue(result)

    def test_code_invalid_beyond_grace_before(self) -> None:
        """Code used outside a grace period should not pass."""
        # Arrange
        self.setUpMembership()
        # we will use a 30-day grace period
        # so set up a membership so that it starts >30 days from today
        self.membership.agreement_start = date.today() + timedelta(days=31)
        self.membership.save()
        code = self.valid_code

        # Act & Assert
        with self.assertRaises(
            MemberCodeValidationError,
            msg=(
                "Membership is inactive "
                f"(start {self.membership.agreement_start}, "
                f"end {self.membership.agreement_end})."
            ),
        ):
            membership_code_valid(code=code, date=self.date, grace_before=30)

    def test_code_valid_beyond_grace_after(self) -> None:
        """Code used outside a grace period should not pass."""
        # Arrange
        self.setUpMembership()
        # we will use a 30-day grace period
        # so set up a membership so that it ends >30 days before today
        self.membership.agreement_end = date.today() - timedelta(days=31)
        self.membership.save()
        code = self.valid_code

        # Act & Assert
        with self.assertRaises(
            MemberCodeValidationError,
            msg=(
                "Membership is inactive "
                f"(start {self.membership.agreement_start}, "
                f"end {self.membership.agreement_end})."
            ),
        ):
            membership_code_valid(code=code, date=self.date, grace_after=30)

    def test_code_no_seats_remaining(self) -> None:
        """Code with no seats remaining should not pass."""
        # Arrange
        self.setUpMembership()
        self.setUpUsedSeats()
        code = self.valid_code

        # Act & Assert
        with self.assertRaises(MemberCodeValidationError, msg="Membership has no training seats remaining."):
            membership_code_valid_training(code=code, date=self.date)

    def test_code_only_public_seats_remaining(self) -> None:
        """Code with only public seats remaining should pass."""
        # Arrange
        self.setUpMembership()
        self.setUpUsedSeats()
        self.task_public.delete()
        code = self.valid_code

        # Act
        result = membership_code_valid_training(
            code=code,
            date=self.date,
        )

        # Assert
        self.assertTrue(result)

    def test_member_code_validation__code_only_inhouse_seats_remaining(self) -> None:
        """Code with only inhouse seats remaining should pass."""
        # Arrange
        self.setUpMembership()
        self.setUpUsedSeats()
        self.task_inhouse.delete()
        code = self.valid_code

        # Act
        result = membership_code_valid_training(
            code=code,
            date=self.date,
        )

        # Assert
        self.assertTrue(result)


class TestGetMembershipOrNoneFromCode(TestBase):
    def setUp(self) -> None:
        self.valid_code = "valid123"
        self.membership = Membership.objects.create(
            name="Alpha Organization",
            variant="bronze",
            agreement_start=date.today() - timedelta(weeks=26),
            agreement_end=date.today() + timedelta(weeks=26),
            contribution_type="financial",
            registration_code=self.valid_code,
            public_instructor_training_seats=1,
            inhouse_instructor_training_seats=1,
        )

    def test_returns_none_if_code_empty(self) -> None:
        # Act
        result_empty_string = get_membership_or_none_from_code("")
        result_none = get_membership_or_none_from_code(None)

        # Assert
        self.assertIsNone(result_empty_string)
        self.assertIsNone(result_none)

    def test_returns_none_if_no_match(self) -> None:
        # Act
        result = get_membership_or_none_from_code("invalid")

        # Assert
        self.assertIsNone(result)

    def test_returns_matching_membership(self) -> None:
        # Act
        result = get_membership_or_none_from_code(self.valid_code)

        # Assert
        self.assertEqual(result, self.membership)


class TestAcceptTrainingRequestAndMatchToEvent(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpTags()
        self._setUpRoles()
        self.valid_code = "valid123"
        self.membership = Membership.objects.create(
            name="Alpha Organization",
            variant="bronze",
            agreement_start=date.today() - timedelta(weeks=26),
            agreement_end=date.today() + timedelta(weeks=26),
            contribution_type="financial",
            registration_code=self.valid_code,
            public_instructor_training_seats=1,
            inhouse_instructor_training_seats=1,
        )
        # set up an event that happens during the membership
        self.event = Event.objects.create(
            start=date.today() + timedelta(weeks=2),
            slug="event-ttt",
            host=self.org_beta,
        )
        self.event.tags.add(Tag.objects.get(name="TTT"))
        self.role = Role.objects.get(name="learner")

    def test_accepts_request(self) -> None:
        # Arrange
        request = create_training_request("p", self.spiderman, open_review=False, reg_code="invalid")

        # Act
        accept_training_request_and_match_to_event(
            request=request,
            event=self.event,
            role=self.role,
            seat_public=True,
            seat_open_training=False,
            seat_membership=self.membership,
        )

        # Assert
        self.assertEqual(request.state, "a")

    def test_creates_task(self) -> None:
        # Arrange
        request = create_training_request("p", self.spiderman, open_review=False, reg_code="invalid")

        # Act
        result = accept_training_request_and_match_to_event(
            request=request,
            event=self.event,
            role=self.role,
            seat_public=True,
            seat_open_training=False,
            seat_membership=self.membership,
        )

        # Assert
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.all()[0], result)
        self.assertEqual(result.person, self.spiderman)
        self.assertEqual(result.event, self.event)
        self.assertEqual(result.role, self.role)
        self.assertEqual(result.seat_public, True)
        self.assertEqual(result.seat_open_training, False)
        self.assertEqual(result.seat_membership, self.membership)

    def test_creates_task_linked_to_benefit(self) -> None:
        # Arrange
        request = create_training_request("p", self.spiderman, open_review=False, reg_code="invalid")
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=self.org_beta,
        )
        benefit = Benefit.objects.create(name="Seat Benefit", unit_type="seat", credits=1)
        account_benefit = AccountBenefit.objects.create(
            account=account,
            benefit=benefit,
            start_date=date.today() - timedelta(days=1),
            end_date=date.today() + timedelta(days=30),
            allocation=1,
        )

        # Act
        result = accept_training_request_and_match_to_event(
            request=request,
            event=self.event,
            role=self.role,
            allocated_benefit=account_benefit,
        )

        # Assert
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.all()[0], result)
        self.assertEqual(result.person, self.spiderman)
        self.assertEqual(result.event, self.event)
        self.assertEqual(result.role, self.role)
        self.assertEqual(result.seat_public, True)
        self.assertEqual(result.seat_open_training, False)
        self.assertEqual(result.seat_membership, None)
        self.assertEqual(result.allocated_benefit, account_benefit)

    def test_returns_existing_task(self) -> None:
        # Arrange
        request = create_training_request("p", self.spiderman, open_review=False, reg_code="invalid")
        Task.objects.create(
            person=self.spiderman,
            event=self.event,
            role=self.role,
            seat_membership=None,
            seat_public=True,
            seat_open_training=True,
        )

        # Act
        result = accept_training_request_and_match_to_event(
            request=request,
            event=self.event,
            role=self.role,
            seat_public=False,
            seat_open_training=False,
            seat_membership=self.membership,
        )

        # Assert
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.all()[0], result)
        self.assertEqual(result.seat_public, True)
        self.assertEqual(result.seat_open_training, True)
        self.assertEqual(result.seat_membership, None)


class TestGetMembershipWarningsAfterMatch(TestBase):
    def setUp(self) -> None:
        self._setUpOrganizations()
        self._setUpTags()
        self.valid_code = "valid123"
        self.membership = Membership.objects.create(
            name="Alpha Organization",
            variant="bronze",
            agreement_start=date.today() - timedelta(weeks=26),
            agreement_end=date.today() + timedelta(weeks=26),
            contribution_type="financial",
            registration_code=self.valid_code,
            public_instructor_training_seats=1,
            inhouse_instructor_training_seats=1,
        )
        # set up an event that happens during the membership
        self.event = Event.objects.create(
            start=date.today() + timedelta(weeks=2),
            slug="event-ttt",
            host=self.org_beta,
        )
        self.event.tags.add(Tag.objects.get(name="TTT"))

    def test_warns_no_seats_remaining__public(self) -> None:
        # Arrange
        self.membership.public_instructor_training_seats = 0
        self.membership.save()
        expected = [
            f'Membership "{self.membership}" is using more training seats than it\'s been allowed.',
        ]

        # Act
        result = get_membership_warnings_after_match(self.membership, seat_public=True, event=self.event)

        # Assert
        self.assertListEqual(expected, result)

    def test_warns_no_seats_remaining__inhouse(self) -> None:
        # Arrange
        self.membership.inhouse_instructor_training_seats = 0
        self.membership.save()
        expected = [
            f'Membership "{self.membership}" is using more training seats than it\'s been allowed.',
        ]

        # Act
        result = get_membership_warnings_after_match(self.membership, seat_public=False, event=self.event)

        # Assert
        self.assertListEqual(expected, result)

    def test_warns_membership_not_active(self) -> None:
        # Arrange
        self.membership.agreement_start = date.today() + timedelta(days=1)
        self.membership.save()
        expected = [
            f'Membership "{self.membership}" is not active.',
        ]

        # Act
        result = get_membership_warnings_after_match(self.membership, seat_public=True, event=self.event)

        # Assert
        self.assertListEqual(expected, result)

    def test_warns_event_outside_membership_dates__early_start(self) -> None:
        # Arrange
        self.event.start = self.membership.agreement_start - timedelta(days=1)
        self.event.save()
        expected = [
            f'Training "{self.event}" has start or end date outside membership "{self.membership}" agreement dates.',
        ]

        # Act
        result = get_membership_warnings_after_match(self.membership, seat_public=True, event=self.event)

        # Assert
        self.assertListEqual(expected, result)

    def test_warns_event_outside_membership_dates__early_end(self) -> None:
        # Arrange
        # create a case where the end of the event is before the start
        # this shouldn't happen in reality but allows us to check the logic
        self.event.end = self.membership.agreement_start - timedelta(days=1)
        self.event.save()
        expected = [
            f'Training "{self.event}" has start or end date outside membership "{self.membership}" agreement dates.',
        ]

        # Act
        result = get_membership_warnings_after_match(self.membership, seat_public=True, event=self.event)

        # Assert
        self.assertListEqual(expected, result)

    def test_warns_event_outside_membership_dates__late_start(self) -> None:
        # Arrange
        self.event.start = self.membership.agreement_end + timedelta(days=1)
        self.event.save()
        expected = [
            f'Training "{self.event}" has start or end date outside membership "{self.membership}" agreement dates.',
        ]

        # Act
        result = get_membership_warnings_after_match(self.membership, seat_public=True, event=self.event)

        # Assert
        self.assertListEqual(expected, result)

    def test_warns_event_outside_membership_dates__late_end(self) -> None:
        # Arrange
        self.event.end = self.membership.agreement_end + timedelta(days=1)
        self.event.save()
        expected = [
            f'Training "{self.event}" has start or end date outside membership "{self.membership}" agreement dates.',
        ]

        # Act
        result = get_membership_warnings_after_match(self.membership, seat_public=True, event=self.event)

        # Assert
        self.assertListEqual(expected, result)

    def test_multiple_warnings(self) -> None:
        # Arrange
        self.membership.public_instructor_training_seats = 0
        self.membership.agreement_start = date.today() + timedelta(days=1)
        self.membership.save()
        self.event.start = self.membership.agreement_end + timedelta(days=1)
        self.event.end = self.event.start + timedelta(days=1)
        self.event.save()
        expected = [
            f'Membership "{self.membership}" is using more training seats than it\'s been allowed.',
            f'Membership "{self.membership}" is not active.',
            f'Training "{self.event}" has start or end date outside membership "{self.membership}" agreement dates.',
        ]

        # Act
        result = get_membership_warnings_after_match(self.membership, seat_public=True, event=self.event)

        # Assert
        self.assertListEqual(expected, result)


class TestGetEventbriteIdFromUrl(TestCase):
    def test_long_url(self) -> None:
        # Arrange
        url = "https://www.eventbrite.com/e/online-instructor-training-7-8-november-2023-tickets-711575811407?aff=oddtdtcreator"  # noqa: E501

        # Act
        result = get_eventbrite_id_from_url_or_return_input(url)

        # Assert
        self.assertEqual(result, "711575811407")

    def test_short_url(self) -> None:
        # Arrange
        url = "https://www.eventbrite.com/e/711575811407"

        # Act
        result = get_eventbrite_id_from_url_or_return_input(url)

        # Assert
        self.assertEqual(result, "711575811407")

    def test_admin_url(self) -> None:
        # Arrange
        url = "https://www.eventbrite.com/myevent?eid=711575811407"

        # Act
        result = get_eventbrite_id_from_url_or_return_input(url)

        # Assert
        self.assertEqual(result, "711575811407")


class TestGetAccountBenefitWarningsAfterMatch(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpRoles()

        # create a benefit and account + account benefit
        self.benefit = Benefit.objects.create(name="Seat Benefit", unit_type="seat", credits=1)
        self.account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=self.org_beta,
        )

    def make_account_benefit(
        self,
        *,
        allocation: int = 1,
        frozen: bool = False,
        start_offset: int = -1,
        end_offset: int = 1,
    ) -> AccountBenefit:
        return AccountBenefit.objects.create(
            account=self.account,
            benefit=self.benefit,
            start_date=date.today() + timedelta(days=start_offset),
            end_date=date.today() + timedelta(days=end_offset),
            allocation=allocation,
            frozen=frozen,
        )

    def test_warns_allocation_exceeded(self) -> None:
        # Arrange
        acc_benefit = self.make_account_benefit(allocation=1, frozen=False)
        event = Event.objects.create(slug="ev1", host=self.org_beta, start=date.today())
        role = Role.objects.get(name="learner")
        # create two tasks allocated to the same benefit (exceeds allocation)
        Task.objects.create(event=event, person=self.spiderman, role=role, allocated_benefit=acc_benefit)
        Task.objects.create(event=event, person=self.blackwidow, role=role, allocated_benefit=acc_benefit)

        # Act
        result = get_account_benefit_warnings_after_match(acc_benefit, event)

        # Assert
        self.assertEqual(len(result), 1)
        self.assertIn("exceeding", result[0])
        self.assertIn(str(acc_benefit.allocation), result[0])

    def test_warns_frozen(self) -> None:
        # Arrange
        acc_benefit = self.make_account_benefit(allocation=10, frozen=True)
        # event within benefit dates to avoid triggering the event date warning
        event = Event.objects.create(slug="ev-frozen", host=self.org_beta, start=date.today())

        # Act
        result = get_account_benefit_warnings_after_match(acc_benefit, event)

        # Assert
        self.assertIn(f'The benefit "{acc_benefit}" has been frozen.', result)

    def test_warns_inactive(self) -> None:
        # Arrange - benefit that expired yesterday
        acc_benefit = self.make_account_benefit(allocation=10, start_offset=-10, end_offset=-1)
        # event within benefit dates to test only the inactive warning
        event = Event.objects.create(slug="ev-inactive", host=self.org_beta, start=date.today() + timedelta(days=-5))

        # Act
        result = get_account_benefit_warnings_after_match(acc_benefit, event)

        # Assert
        self.assertIn(f'The benefit "{acc_benefit}" is outside its valid dates.', result)

    def test_warns_event_outside_benefit_dates(self) -> None:
        # Arrange - benefit valid for next week, event starting today (outside)
        account_benefit = self.make_account_benefit(allocation=10, start_offset=3, end_offset=10)
        event = Event.objects.create(slug="ev-outside", host=self.org_beta, start=date.today())

        # Act
        results = get_account_benefit_warnings_after_match(account_benefit, event)

        # Assert
        self.assertIn(
            f'"{event}" has start or end date outside account benefit "{account_benefit}" valid dates.',
            results,
        )

    def test_no_event_date_warning_when_event_within_benefit_dates(self) -> None:
        # Arrange
        account_benefit = self.make_account_benefit(allocation=10)
        event = Event.objects.create(slug="ev-inside", host=self.org_beta, start=date.today())

        # Act
        results = get_account_benefit_warnings_after_match(account_benefit, event)

        # Assert
        self.assertFalse(any("outside account benefit" in w for w in results))


class TestGetAccountBenefitFromPartnership(TestBase):
    def setUp(self) -> None:
        super().setUp()
        self._setUpRoles()

        self.benefit = Benefit.objects.create(name="Instructor Training", unit_type="seat", credits=1)
        self.account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=self.org_beta,
        )
        tier = PartnershipTier.objects.create(name="Standard", credits=10)
        self.partnership = Partnership.objects.create(
            name="Partner Org",
            tier=tier,
            credits=10,
            account=self.account,
            registration_code="partner-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            agreement_link="https://example.com/agreement",
            public_status="public",
            partner_organisation=self.org_beta,
        )

    def make_account_benefit(self, *, allocation: int, start_date_offset: int = 0) -> AccountBenefit:
        return AccountBenefit.objects.create(
            account=self.account,
            benefit=self.benefit,
            partnership=self.partnership,
            start_date=date.today() + timedelta(days=start_date_offset),  # to ensure ordering
            end_date=date.today() + timedelta(days=365),
            allocation=allocation,
        )

    def allocate_benefit(self, account_benefit: AccountBenefit, count: int) -> None:
        event = Event.objects.create(slug=f"ev-{account_benefit.pk}", host=self.org_beta)
        role = Role.objects.get(name="learner")
        people = [self.spiderman, self.blackwidow, self.ironman]
        for i in range(count):
            Task.objects.create(event=event, person=people[i], role=role, allocated_benefit=account_benefit)

    def test_returns_first_with_remaining_allocation(self) -> None:
        # Arrange - two benefits; first is fully allocated, second has room
        benefit1 = self.make_account_benefit(allocation=1, start_date_offset=-1)
        benefit2 = self.make_account_benefit(allocation=5)
        self.allocate_benefit(benefit1, 1)  # exhaust benefit1

        # Act
        result = get_account_benefit_from_partnership(self.partnership, self.benefit)

        # Assert
        self.assertEqual(result, benefit2)

    def test_returns_last_when_all_exhausted(self) -> None:
        # Arrange - two benefits, both fully allocated
        benefit1 = self.make_account_benefit(allocation=1, start_date_offset=-1)
        benefit2 = self.make_account_benefit(allocation=1)
        self.allocate_benefit(benefit1, 1)
        self.allocate_benefit(benefit2, 1)

        # Act - should return last one (benefit2, ordered by start_date)
        result = get_account_benefit_from_partnership(self.partnership, self.benefit)

        # Assert
        self.assertEqual(result, benefit2)

    def test_raises_does_not_exist_when_no_benefits(self) -> None:
        # Arrange - no account benefits exist for this partnership+benefit
        other_benefit = Benefit.objects.create(name="Other Benefit", unit_type="seat", credits=1)

        # Act & Assert
        with self.assertRaises(AccountBenefit.DoesNotExist):
            get_account_benefit_from_partnership(self.partnership, other_benefit)
