import re
from datetime import date, timedelta

from src.fiscal.models import Partnership
from src.offering.models import AccountBenefit, Benefit
from src.workshops.models import Event, Membership, Role, Task, TrainingRequest

# ----------------------------------------
# Utilities for validating member codes
# ----------------------------------------

type CodeValidationResult = tuple[bool, str]  # (is_valid, reason)


def membership_code_valid(code: str, date: date, grace_before: int = 0, grace_after: int = 0) -> CodeValidationResult:
    """Returns True if `code` matches an Membership that is active on `date`,
    including a grace period of `grace_before` days before
    and `grace_after` days after the Membership dates.
    If there is no match, returns False with a detailed error.
    """
    try:
        # Find relevant membership - may raise Membership.DoesNotExist
        membership = Membership.objects.get(registration_code=code)
    except Membership.DoesNotExist:
        return False, f'No membership found for code "{code}".'

    # Confirm that membership was active at the time the request was submitted.
    # Grace period: 90 days before and after
    if not membership.active_on_date(date, grace_before=grace_before, grace_after=grace_after):
        return False, (f"Membership is inactive (start {membership.agreement_start}, end {membership.agreement_end}).")

    return True, "Membership is valid."


def membership_code_valid_training(
    code: str, date: date, grace_before: int = 0, grace_after: int = 0
) -> CodeValidationResult:
    """Returns True if `code` matches an active Membership with training seats
    remaining. If there is no match, returns False with a detailed error."""
    # First ensure the code matches an active membership.
    result, reason = membership_code_valid(code=code, date=date, grace_before=grace_before, grace_after=grace_after)
    if not result:
        return result, reason

    # Find relevant membership - should definitely exist.
    membership = Membership.objects.get(registration_code=code)

    # Confirm that membership has training seats remaining.
    if (
        membership.public_instructor_training_seats_remaining + membership.inhouse_instructor_training_seats_remaining
        <= 0
    ):
        return False, "Membership has no training seats remaining."

    return True, "Membership has training seats remaining."


def partnership_code_valid(code: str, date: date, grace_before: int = 0, grace_after: int = 0) -> CodeValidationResult:
    """Returns True if `code` matches a Partnership that is active on `date`,
    including a grace period of `grace_before` days before
    and `grace_after` days after the Partnership dates.
    If there is no match, returns False with a detailed error.
    """
    try:
        partnership = Partnership.objects.get(registration_code=code)
    except Partnership.DoesNotExist:
        return False, f'No partnership found for code "{code}".'

    start_date = partnership.agreement_start - timedelta(days=grace_before)
    end_date = partnership.agreement_end + timedelta(days=grace_after)

    if not (start_date <= date <= end_date):
        return False, f"Partnership is inactive (start {partnership.agreement_start}, end {partnership.agreement_end})."

    return True, "Partnership is valid."


def account_benefit_code_valid(
    code: str, date: date, grace_before: int = 0, grace_after: int = 0
) -> CodeValidationResult:
    """Returns True if `code` matches an AccountBenefit that is active on `date`,
    including a grace period of `grace_before` days before
    and `grace_after` days after the AccountBenefit dates, and if it is not frozen and has allocation remaining.
    If there is no match, returns False with a detailed error.
    """
    try:
        account_benefit = AccountBenefit.objects.get(registration_code=code)
    except AccountBenefit.DoesNotExist:
        return False, f'No account benefit found for code "{code}".'

    start_date = account_benefit.start_date - timedelta(days=grace_before)
    end_date = account_benefit.end_date + timedelta(days=grace_after)

    if not (start_date <= date <= end_date):
        return (
            False,
            f"Account benefit is inactive (start {account_benefit.start_date}, end {account_benefit.end_date}).",
        )

    if account_benefit.frozen:
        return False, "Account benefit has been frozen."

    if account_benefit.allocation_used() >= account_benefit.allocation:
        return False, "Account benefit has no allocation remaining."

    return True, "Account benefit is valid."


def any_member_code_valid(code: str, date: date, grace_before: int = 0, grace_after: int = 0) -> bool:
    """Returns True if `code` matches any active Membership, Partnership, or AccountBenefit."""
    for validator in [membership_code_valid, partnership_code_valid, account_benefit_code_valid]:
        is_valid, _ = validator(code=code, date=date, grace_before=grace_before, grace_after=grace_after)
        if is_valid:  # Exit early if any validator returns True
            return True
    return False


def any_member_code_valid_training(code: str, date: date, grace_before: int = 0, grace_after: int = 0) -> bool:
    """Returns True if `code` matches any active Membership with training seats, Partnership,
    or AccountBenefit with allocation remaining."""
    for validator in [membership_code_valid_training, partnership_code_valid, account_benefit_code_valid]:
        is_valid, _ = validator(code=code, date=date, grace_before=grace_before, grace_after=grace_after)
        if is_valid:  # Exit early if any validator returns True
            return True
    return False


def get_membership_or_none_from_code(code: str | None) -> Membership | None:
    """Given a member code, returns the related membership
    or None if no such membership exists. If provided an empty code, returns None."""
    if not code:
        return None

    return Membership.objects.filter(registration_code=code).first()


def get_partnership_or_none_from_code(code: str | None) -> Partnership | None:
    """Given a partnership code, returns the related partnership
    or None if no such partnership exists. If provided an empty code, returns None."""
    if not code:
        return None

    return Partnership.objects.filter(registration_code=code).first()


# ----------------------------------------
# Utilities for matching training requests
# ----------------------------------------


def accept_training_request_and_match_to_event(
    request: TrainingRequest,
    event: Event,
    role: Role,
    seat_public: bool = True,  # default value taken from Task model
    seat_open_training: bool = False,  # default value taken from Task model
    seat_membership: Membership | None = None,
    allocated_benefit: AccountBenefit | None = None,
) -> Task:
    # accept the request
    request.state = "a"
    request.save()

    # assign to an event
    task, _ = Task.objects.get_or_create(
        event=event,
        person=request.person,
        role=role,
        defaults=dict(
            seat_membership=seat_membership,
            seat_public=seat_public,
            seat_open_training=seat_open_training,
            allocated_benefit=allocated_benefit,
        ),
    )

    return task


def get_membership_warnings_after_match(membership: Membership, seat_public: bool, event: Event) -> list[str]:
    """Returns a list of warnings based on membership remaining seats
    and start/end dates."""
    warnings = []

    remaining = (
        membership.public_instructor_training_seats_remaining
        if seat_public
        else membership.inhouse_instructor_training_seats_remaining
    )
    if remaining <= 0:
        warnings.append(
            f'Membership "{membership}" is using more training seats than it\'s been allowed.',
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
            f'Training "{event}" has start or end date outside membership "{membership}" agreement dates.',
        )

    return warnings


def get_account_benefit_warnings_after_match(benefit: AccountBenefit, event: Event) -> list[str]:
    """Returns a list of warnings based on allocated benefit usage
    and start/end dates."""
    warnings = []

    used = benefit.allocation_used()
    if used > benefit.allocation:
        warnings.append(
            f'The benefit "{benefit}" is exceeding ({used}) allocation ({benefit.allocation}).',
        )

    if benefit.frozen:
        warnings.append(f'The benefit "{benefit}" has been frozen.')

    if not benefit.active():
        warnings.append(
            f'The benefit "{benefit}" is outside its valid dates.',
        )

    # show warning if training falls out of account benefit dates
    if (
        event.start
        and not (benefit.start_date <= event.start <= benefit.end_date)
        or event.end
        and not (benefit.start_date <= event.end <= benefit.end_date)
    ):
        warnings.append(
            f'"{event}" has start or end date outside account benefit "{benefit}" valid dates.',
        )

    return warnings


def get_account_benefit_from_partnership(partnership: Partnership, benefit: Benefit) -> AccountBenefit:
    account_benefits = AccountBenefit.objects.filter(partnership=partnership, benefit=benefit).order_by("start_date")
    if not account_benefits:
        raise AccountBenefit.DoesNotExist(
            f'No account benefits found for partnership "{partnership}" and benefit "{benefit}".'
        )

    for account_benefit in account_benefits:
        # return the first account benefit that has allocation remaining
        if account_benefit.allocation_used() < account_benefit.allocation:
            return account_benefit

    # if all account benefits are fully used, return the last one
    return account_benefit


# ----------------------------------------
# Utilities for Eventbrite URLs
# ----------------------------------------

# Eventbrite IDs are long strings of digits (~12 characters)
EVENTBRITE_ID_PATTERN = re.compile(r"\d{10,}")

# regex to cover known forms of Eventbrite URL that trainees could provide
# https://www.eventbrite.com/e/event-name-123456789012
# https://www.eventbrite.com/e/123456789012
# plus a possible query at the end e.g. ?aff=oddtdtcreator
# and considering localised domains such as .co.uk and .fr
EVENTBRITE_URL_PATTERN = re.compile(
    r"^(https?:\/\/)?"  # optional https://
    r"www\.eventbrite\."
    r"(com|co\.uk|[a-z]{2})"  # possible domains - .com, .co.uk, 2-letter country domain
    r"\/e\/"  # /e/ should always be present at start of path
    r"[a-z0-9\-]+"  # optional event-name
    r"\d{10,}"  # event ID
    r"($|\?)",  # end of string or beginning of query (?)
)


def get_eventbrite_id_from_url_or_return_input(url: str) -> str:
    """Given the URL for an Eventbrite event, returns that event's ID.
    If the ID can't be found, returns the input URL."""
    match = re.search(EVENTBRITE_ID_PATTERN, url)
    return match.group() if match else url
