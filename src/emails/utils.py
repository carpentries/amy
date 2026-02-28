import logging
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, time, timedelta
from functools import partial
from typing import Any, Literal, TypeVar, cast
from urllib.parse import ParseResult, urlparse

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.db.models import Model
from django.http import HttpRequest
from django.utils import timezone
from django.utils.html import format_html
from flags import conditions  # type: ignore[import-untyped]
from jinja2 import Environment
from rest_framework.serializers import ModelSerializer

from src.api.v2.serializers import (
    AwardSerializer,
    ConsortiumSerializer,
    EventSerializer,
    InstructorRecruitmentSignupSerializer,
    MembershipSerializer,
    OrganizationSerializer,
    PartnershipSerializer,
    PersonSerializer,
    SelfOrganisedSubmissionSerializer,
    TaskSerializer,
    TrainingProgressSerializer,
    TrainingRequirementSerializer,
)
from src.emails.models import ScheduledEmail
from src.emails.signals import Signal
from src.extrequests.models import SelfOrganisedSubmission
from src.fiscal.models import Consortium, Partnership
from src.recruitment.models import InstructorRecruitmentSignup
from src.workshops.models import (
    Award,
    Event,
    Membership,
    Organization,
    Person,
    Task,
    TrainingProgress,
    TrainingRequirement,
)

logger = logging.getLogger("amy")

BasicTypes = str | int | float | bool | datetime | None
SerializedData = dict[str, Any] | BasicTypes
_MT = TypeVar("_MT", bound=Model)  # Model type


@conditions.register("session")  # type: ignore
def session_condition(value: str, request: HttpRequest, **kwargs: Any) -> bool:
    """Additional condition for django-flags. It reads a specific value from
    request session."""
    return cast(bool, request.session.get(value, False))


def immediate_action() -> datetime:
    """Timezone-aware datetime object for immediate action (supposed to run after
    1 hour from being scheduled)."""
    return timezone.now() + timedelta(hours=1)


def combine_date_with_set_time(date: date, time_: time) -> datetime:
    """Return timezone-aware datetime object combining set time with a given date."""
    if time_.tzinfo is None:
        raise ValueError("time parameter must not be naive")
    return datetime.combine(date, time_)


def combine_date_with_current_utc_time(date: date) -> datetime:
    """Return timezone-aware datetime object combining current time in UTC
    with a given date."""
    current_time_utc = datetime.now(UTC).timetz()
    return combine_date_with_set_time(date, current_time_utc)


def shift_date_and_apply_set_time(date: date, offset: timedelta, time_: time) -> datetime:
    """Return timezone-aware datetime object combining current time in UTC
    with a given date shifted by offset (timedelta).
    Time component of the offset is discarded."""
    date_shifted = date + offset
    return combine_date_with_set_time(date_shifted, time_)


def shift_date_and_apply_current_utc_time(date: date, offset: timedelta) -> datetime:
    """Return timezone-aware datetime object combining current time in UTC
    with a given date shifted by offset (timedelta).
    Time component of the offset is discarded."""
    date_shifted = date + offset
    return combine_date_with_current_utc_time(date_shifted)


one_month_before = partial(shift_date_and_apply_current_utc_time, offset=-timedelta(days=30))
two_months_after = partial(shift_date_and_apply_current_utc_time, offset=timedelta(days=60))


def messages_missing_recipients(request: HttpRequest, signal: str) -> None:
    messages.warning(
        request,
        f"Email action was not scheduled due to missing recipients for signal {signal}."
        " Please check if the persons involved have email addresses set.",
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_missing_template(request: HttpRequest, signal: str) -> None:
    messages.warning(
        request,
        f"Email action was not scheduled due to missing template for signal {signal}.",
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_missing_template_link(request: HttpRequest, scheduled_email: ScheduledEmail) -> None:
    messages.warning(
        request,
        f'Email action <a href="{scheduled_email.get_absolute_url}">'
        f"<code>{scheduled_email.pk}</code></a> update was not performed due"
        " to missing linked template.",
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_action_scheduled(request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail) -> None:
    name = scheduled_email.template.name if scheduled_email.template else signal_name
    messages.info(
        request,
        format_html(
            "New email action was scheduled to run "
            '<relative-time datetime="{}"></relative-time>: '
            '<a href="{}"><code>{}</code></a>.',
            scheduled_email.scheduled_at,
            scheduled_email.get_absolute_url(),
            name,
        ),
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_action_updated(request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail) -> None:
    name = scheduled_email.template.name if scheduled_email.template else signal_name
    messages.info(
        request,
        format_html(
            'Existing <a href="{}">email action ({})</a> was updated.',
            scheduled_email.get_absolute_url(),
            name,
        ),
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_action_cancelled(request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail) -> None:
    name = scheduled_email.template.name if scheduled_email.template else signal_name
    messages.warning(
        request,
        format_html(
            'Existing <a href="{}">email action ({})</a> was cancelled.',
            scheduled_email.get_absolute_url(),
            name,
        ),
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def person_from_request(request: HttpRequest) -> Person | None:
    """Simplify getting person from request, or None if they're not authenticated."""
    if (
        not hasattr(request, "user")  # field often not present in unit tests
        or not request.user.is_authenticated  # don't return AnonymousUser
    ):
        return None

    return request.user


def find_signal_by_name(signal_name: str, all_signals: Iterable[Signal]) -> Signal | None:
    return next(
        (signal for signal in all_signals if signal.signal_name == signal_name),
        None,
    )


def api_model_url(model: str, pk: int) -> str:
    return f"api:{model}#{pk}"


def scalar_value_url(type_: Literal["str", "int", "float", "bool", "date", "none"], value: str) -> str:
    return f"value:{type_}#{value}"


scalar_value_none = partial(scalar_value_url, "none", "")


def log_condition_elements(**condition_elements: Any) -> None:
    logger.debug(f"{condition_elements=}")


def jinjanify(engine: Environment, template: str, context: dict[str, Any]) -> str:
    return engine.from_string(template).render(context)


def scalar_value_from_type(type_: str, value: Any) -> BasicTypes:
    mapping: dict[str, Callable[[Any], Any]] = {
        "str": str,
        "int": int,
        "float": float,
        "bool": lambda x: x.lower() in ("true", "t", "1"),
        "date": datetime.fromisoformat,
        "none": lambda _: None,
    }

    try:
        return cast(BasicTypes, mapping[type_](value))
    except KeyError as exc:
        raise ValueError(f"Unsupported scalar type {type_!r} (value {value!r}).") from exc
    except ValueError as exc:
        raise ValueError(f"Failed to parse {value!r} for type {type_!r}.") from exc


def find_model_class(model_name: str) -> type[Model]:
    model_class = next(
        (model for model in apps.get_models() if model._meta.model_name == model_name),
        None,
    )
    if model_class is None:
        raise ValueError(f"Model {model_name!r} not found.")
    return model_class


def find_model_instance(model_class: type[Model], model_pk: Any) -> Model:
    try:
        return model_class.objects.get(pk=model_pk)  # type: ignore
    except ValueError as exc:
        raise ValueError(f"Failed to parse pk {model_pk!r} for model {model_class!r}: {exc}") from exc
    except model_class.DoesNotExist as exc:  # type: ignore
        raise ValueError(f"Model {model_class!r} with pk {model_pk!r} not found.") from exc


def map_single_api_uri_to_value(uri: str) -> BasicTypes:
    match urlparse(uri):
        case ParseResult(scheme="value", netloc="", path=type_, params="", query="", fragment=value):
            return scalar_value_from_type(type_, value)
        case _:
            raise ValueError(f"Unsupported URI {uri!r}.")


def map_single_api_uri_to_serialized_model(uri: str) -> dict[str, Any]:
    # to prevent circular import:
    from src.api.v2.serializers import ScheduledEmailSerializer

    ModelToSerializerMapper: dict[type[_MT], type[ModelSerializer[_MT]]] = {  # type: ignore
        Award: AwardSerializer,
        Consortium: ConsortiumSerializer,
        Organization: OrganizationSerializer,
        Event: EventSerializer,
        InstructorRecruitmentSignup: InstructorRecruitmentSignupSerializer,
        Membership: MembershipSerializer,
        Partnership: PartnershipSerializer,
        Person: PersonSerializer,
        ScheduledEmail: ScheduledEmailSerializer,
        Task: TaskSerializer,
        TrainingProgress: TrainingProgressSerializer,
        TrainingRequirement: TrainingRequirementSerializer,
        SelfOrganisedSubmission: SelfOrganisedSubmissionSerializer,
    }

    match urlparse(uri):
        case ParseResult(scheme="api", netloc="", path=model_name, params="", query="", fragment=id_):
            try:
                model_class = find_model_class(model_name)
                model_instance = find_model_instance(model_class, int(id_))
                serializer = ModelToSerializerMapper[model_class]
                return dict(serializer(model_instance).data)
            except ValueError as exc:
                raise ValueError(f"Failed to parse URI {uri!r}.") from exc

        case _:
            raise ValueError(f"Unsupported URI {uri!r}.")


def map_single_api_uri_to_serialized_model_or_value(uri: str) -> SerializedData:
    match urlparse(uri):
        case ParseResult(scheme="value", netloc="", path=_, params="", query="", fragment=_):
            return map_single_api_uri_to_value(uri)

        case ParseResult(scheme="api", netloc="", path=_, params="", query="", fragment=_):
            return map_single_api_uri_to_serialized_model(uri)

        case _:
            raise ValueError(f"Unsupported URI {uri!r}.")


def map_api_uri_to_serialized_model_or_value(
    uri: str | list[str],
) -> SerializedData | list[SerializedData]:
    if isinstance(uri, list):
        return [map_single_api_uri_to_serialized_model_or_value(single_uri) for single_uri in uri]
    return map_single_api_uri_to_serialized_model_or_value(uri)


def build_context_from_dict(context: dict[str, str | list[str]]) -> dict[str, SerializedData | list[SerializedData]]:
    return {key: map_api_uri_to_serialized_model_or_value(uri) for key, uri in context.items()}


def build_context_from_list(context: list[dict[str, str]]) -> list[SerializedData | list[SerializedData]]:
    return [
        (
            map_single_api_uri_to_serialized_model(item["api_uri"]).get(
                item["property"],
                "invalid",
            )
            if "api_uri" in item
            else map_single_api_uri_to_value(item["value_uri"])
        )
        for item in context
    ]
