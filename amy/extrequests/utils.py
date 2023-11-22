from datetime import date

from django.core.exceptions import ValidationError

from workshops.models import Event, Membership


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

    return True


def member_code_valid_training(
    code: str, date: date, grace_before: int = 0, grace_after: int = 0
) -> tuple[bool, str]:
    """Returns True if `code` matches an active Membership with training seats
    remaining. If there is no match, raises an Exception with a detailed error."""
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


def get_membership_or_none_from_code(code: str) -> Membership | None:
    """Given a member code, returns the related membership
    or None if no such membership exists. If provided an empty code, returns None."""
    if not code:
        return None

    try:
        return Membership.objects.get(registration_code=code)
    except Membership.DoesNotExist:
        return None


def get_membership_warnings_after_match(
    membership: Membership, seat_public: bool, event: Event
) -> list[str]:
    warnings = []

    remaining = (
        membership.public_instructor_training_seats_remaining
        if seat_public
        else membership.inhouse_instructor_training_seats_remaining
    )
    if remaining <= 0:
        warnings.append(
            f'Membership "{membership}" is using more training seats than '
            "it's been allowed.",
        )

    # check if membership is active
    if not (membership.agreement_start <= date.today() <= membership.agreement_end):
        warnings.append(
            f'Membership "{membership}" is not active.',
        )

    # show warning if training falls out of agreement dates
    if (
        event.start
        and not (membership.agreement_start <= event.start <= membership.agreement_end)
        or event.end
        and not (membership.agreement_start <= event.end <= membership.agreement_end)
    ):
        warnings.append(
            f'Training "{event}" has start or end date outside '
            f'membership "{membership}" agreement dates.',
        )

    return warnings
