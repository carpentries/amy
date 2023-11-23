from datetime import date
import re

from django.core.exceptions import ValidationError

from workshops.models import Event, Membership, Role, Task, TrainingRequest

# ----------------------------------------
# Utilities for validating member codes
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


# ----------------------------------------
# Utilities for matching training requests
# ----------------------------------------


def get_membership_from_training_request_or_raise_error(
    request: TrainingRequest,
) -> Membership:
    """Returns the Membership associated with a training request,
    if such a Membership can be found."""
    if not request.member_code:
        raise ValueError(
            f"{request}: Request does not include a member registration "
            "code, so cannot be matched to a membership seat."
        )
    try:
        return Membership.objects.get(registration_code=request.member_code)
    except Membership.DoesNotExist:
        raise Membership.DoesNotExist(
            f"{request}: No membership found for registration code "
            f'"{request.member_code}".'
        )


def accept_training_request_and_match_to_event(
    request: TrainingRequest,
    event: Event,
    role: Role,
    seat_public: bool,
    seat_open_training: bool,
    seat_membership: Membership | None = None,
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
        ),
    )

    return task


def get_membership_warnings_after_match(
    membership: Membership, seat_public: bool, event: Event
) -> list[str]:
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


def get_eventbrite_id_from_url_or_return_input(url: str) -> str:
    """Given the URL for an Eventbrite event, returns that event's ID.
    If the ID can't be found, returns the input URL."""
    match = re.search(EVENTBRITE_ID_PATTERN, url)
    return match.group() if match else url
