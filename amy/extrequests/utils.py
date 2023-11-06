from datetime import date

from django.core.exceptions import ValidationError

from workshops.models import Membership


class MemberCodeValidationError(ValidationError):
    pass


def member_code_valid(
    code: str, date: date, grace_before: int = 0, grace_after: int = 0
) -> tuple[bool, str]:
    """Returns True if `code` matches an Membership that is active on `date`,
    including a grace period of `grace_before` days before
    and `grace_after` days after the Membership dates.
    If there is no match, raises an Exception with a detailed error.
    """
    try:
        # find relevant membership - may raise Membership.DoesNotExist
        membership = Membership.objects.get(registration_code=code)
    except Membership.DoesNotExist as e:
        raise MemberCodeValidationError(
            f'No membership found for code "{code}".'
        ) from e

    # confirm that membership was active at the time the request was submitted
    # grace period: 90 days before and after
    if not membership.active_on_date(
        date, grace_before=grace_before, grace_after=grace_after
    ):
        raise MemberCodeValidationError(
            "Membership is inactive "
            f"(start {membership.agreement_start}, "
            f"end {membership.agreement_end})."
        )

    # confirm that membership has training seats remaining
    if (
        membership.public_instructor_training_seats_remaining
        + membership.inhouse_instructor_training_seats_remaining
        <= 0
    ):
        raise MemberCodeValidationError("Membership has no training seats remaining.")

    return True


def member_code_valid_training(
    code: str, date: date, grace_before: int = 0, grace_after: int = 0
) -> tuple[bool, str]:
    """Returns True if `code` matches an active Membership with training seats remaining.
    If there is no match, raises an Exception with a detailed error."""
    # first ensure the code matches an active membership
    try:
        member_code_valid(
            code=code, date=date, grace_before=grace_before, grace_after=grace_after
        )
    except MemberCodeValidationError:
        raise

    # find relevant membership - should definitely exist
    membership = Membership.objects.get(registration_code=code)

    # confirm that membership has training seats remaining
    if (
        membership.public_instructor_training_seats_remaining
        + membership.inhouse_instructor_training_seats_remaining
        <= 0
    ):
        raise MemberCodeValidationError("Membership has no training seats remaining.")

    return True
