from datetime import date, timedelta

from extrequests.utils import (
    MemberCodeValidationError,
    get_membership_from_code_if_exists,
    member_code_valid,
    member_code_valid_training,
)
from workshops.models import Event, Membership, Role, Tag, Task
from workshops.tests.base import TestBase


class TestMemberCodeValid(TestBase):
    def setUp(self):
        self._setUpRoles()
        self.date = date.today()

    def setUpMembership(self):
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

    def setUpUsedSeats(self):
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

    def test_code_valid(self):
        """Valid member code should pass."""
        # Arrange
        self.setUpMembership()
        code = self.valid_code

        # Act
        result = member_code_valid(
            code=code,
            date=self.date,
        )

        # Assert
        self.assertTrue(result)

    def test_code_invalid(self):
        """Invalid member code should not pass."""
        # Arrange
        code = "invalid"

        # Act & Assert
        with self.assertRaises(
            MemberCodeValidationError, msg='No membership found for code "invalid".'
        ):
            member_code_valid(
                code=code,
                date=self.date,
            )

    def test__code_inactive_early(self):
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
            member_code_valid(
                code=code,
                date=test_date,
            )

    def test__code_inactive_late(self):
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
            member_code_valid(
                code=code,
                date=test_date,
            )

    def test_code_valid_within_grace_before(self):
        """Code used within a grace period should pass."""
        # Arrange
        self.setUpMembership()
        # we will use a 30-day grace period
        # so set up a membership so that it starts <30 days from today
        self.membership.agreement_start = date.today() + timedelta(days=29)
        self.membership.save()
        code = self.valid_code

        # Act
        result = member_code_valid(code=code, date=self.date, grace_before=30)

        # Assert
        self.assertTrue(result)

    def test_code_valid_within_grace_after(self):
        """Code used within a grace period should pass."""
        # Arrange
        self.setUpMembership()
        # we will use a 30-day grace period
        # so set up a membership so that it ends <30 days before today
        self.membership.agreement_end = date.today() - timedelta(days=29)
        self.membership.save()
        code = self.valid_code

        # Act
        result = member_code_valid(code=code, date=self.date, grace_after=30)

        # Assert
        self.assertTrue(result)

    def test_code_invalid_beyond_grace_before(self):
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
            member_code_valid(code=code, date=self.date, grace_before=30)

    def test_code_valid_beyond_grace_after(self):
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
            member_code_valid(code=code, date=self.date, grace_after=30)

    def test_code_no_seats_remaining(self):
        """Code with no seats remaining should not pass."""
        # Arrange
        self.setUpMembership()
        self.setUpUsedSeats()
        code = self.valid_code

        # Act & Assert
        with self.assertRaises(
            MemberCodeValidationError, msg="Membership has no training seats remaining."
        ):
            member_code_valid_training(code=code, date=self.date)

    def test_code_only_public_seats_remaining(self):
        """Code with only public seats remaining should pass."""
        # Arrange
        self.setUpMembership()
        self.setUpUsedSeats()
        self.task_public.delete()
        code = self.valid_code

        # Act
        result = member_code_valid_training(
            code=code,
            date=self.date,
        )

        # Assert
        self.assertTrue(result)

    def test_member_code_validation__code_only_inhouse_seats_remaining(self):
        """Code with only inhouse seats remaining should pass."""
        # Arrange
        self.setUpMembership()
        self.setUpUsedSeats()
        self.task_inhouse.delete()
        code = self.valid_code

        # Act
        result = member_code_valid_training(
            code=code,
            date=self.date,
        )

        # Assert
        self.assertTrue(result)


class TestGetMembershipFromCodeIfExists(TestBase):
    def setUp(self):
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

    def test_returns_none_if_code_empty(self):
        # Act
        result_empty_string = get_membership_from_code_if_exists("")
        result_none = get_membership_from_code_if_exists(None)

        # Assert
        self.assertIsNone(result_empty_string)
        self.assertIsNone(result_none)

    def test_returns_none_if_no_match(self):
        # Act
        result = get_membership_from_code_if_exists("invalid")

        # Assert
        self.assertIsNone(result)

    def test_returns_matching_membership(self):
        # Act
        result = get_membership_from_code_if_exists(self.valid_code)

        # Assert
        self.assertEqual(result, self.membership)
