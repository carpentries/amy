from datetime import UTC, date, datetime, timedelta
from functools import partial
import logging
from typing import Any, Callable, Iterable, Literal, cast
from urllib.parse import ParseResult, urlparse

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.db.models import Model
from django.http import HttpRequest
from django.utils import timezone
from django.utils.html import format_html
from flags import conditions
from jinja2 import Environment

from emails.models import ScheduledEmail
from emails.signals import Signal
from workshops.models import Person

logger = logging.getLogger("amy")

BasicTypes = str | int | float | bool | datetime | None


@conditions.register("session")  # type: ignore
def session_condition(value, request: HttpRequest, **kwargs):
    """Additional condition for django-flags. It reads a specific value from
    request session."""
    return request.session.get(value, False)


def immediate_action() -> datetime:
    """Timezone-aware datetime object for immediate action (supposed to run after
    1 hour from being scheduled)."""
    return timezone.now() + timedelta(hours=1)


def combine_date_with_current_utc_time(date: date) -> datetime:
    """Return timezone-aware datetime object combining current time in UTC
    with a given date."""
    current_time_utc = datetime.now(UTC).timetz()
    return datetime.combine(date, current_time_utc)


def shift_date_and_apply_current_utc_time(date: date, offset: timedelta) -> datetime:
    """Return timezone-aware datetime object combining current time in UTC
    with a given date shifted by offset (timedelta).
    Time component of the offset is discarded."""
    date_shifted = date + offset
    return combine_date_with_current_utc_time(date_shifted)


one_month_before = partial(
    shift_date_and_apply_current_utc_time, offset=-timedelta(days=30)
)
two_months_after = partial(
    shift_date_and_apply_current_utc_time, offset=timedelta(days=60)
)


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


def messages_missing_template_link(
    request: HttpRequest, scheduled_email: ScheduledEmail
) -> None:
    messages.warning(
        request,
        f'Email action <a href="{ scheduled_email.get_absolute_url }">'
        f"<code>{ scheduled_email.pk }</code></a> update was not performed due"
        " to missing linked template.",
        extra_tags=settings.ONLY_FOR_ADMINS_TAG,
    )


def messages_action_scheduled(
    request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail
) -> None:
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


def messages_action_updated(
    request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail
) -> None:
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


def messages_action_cancelled(
    request: HttpRequest, signal_name: str, scheduled_email: ScheduledEmail
) -> None:
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

    return cast(Person, request.user)


def find_signal_by_name(
    signal_name: str, all_signals: Iterable[Signal]
) -> Signal | None:
    return next(
        (signal for signal in all_signals if signal.signal_name == signal_name),
        None,
    )


def api_model_url(model: str, pk: int) -> str:
    return f"api:{model}#{pk}"


def scalar_value_url(
    type_: Literal["str", "int", "float", "bool", "date", "none"], value: str
) -> str:
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
        "bool": lambda x: x.lower() == "true",
        "date": datetime.fromisoformat,
        "none": lambda _: None,
    }

    try:
        return cast(BasicTypes, mapping[type_](value))
    except KeyError as exc:
        raise ValueError(f"Unsupported scalar type {type_!r}.") from exc
    except ValueError as exc:
        raise ValueError(f"Failed to parse {value!r}.") from exc


def find_model_instance(model_name: str, model_pk: int) -> Model:
    model = next(
        (model for model in apps.get_models() if model._meta.model_name == model_name),
        None,
    )
    if model is None:
        raise ValueError(f"Model {model_name!r} not found.")

    try:
        return model.objects.get(pk=model_pk)
    except model.DoesNotExist as exc:
        raise ValueError(
            f"Model {model_name!r} with pk {model_pk!r} not found."
        ) from exc


def map_single_api_uri_to_model_or_value(uri: str) -> Model | BasicTypes:
    match urlparse(uri):
        case ParseResult(
            scheme="value", netloc="", path=type_, params="", query="", fragment=value
        ):
            return scalar_value_from_type(type_, value)

        case ParseResult(
            scheme="api", netloc="", path=model_name, params="", query="", fragment=id_
        ):
            return find_model_instance(model_name, int(id_))

        case _:
            raise ValueError(f"Unsupported URI {uri!r}.")


def map_api_uri_to_model_or_value(
    uri: str | list[str],
) -> BasicTypes | Model | list[Model | BasicTypes]:
    if isinstance(uri, list):
        return [map_single_api_uri_to_model_or_value(single_uri) for single_uri in uri]
    return map_single_api_uri_to_model_or_value(uri)


def build_context_from_dict(
    context_json: dict[str, str]
) -> dict[str, BasicTypes | Model | list[Model | BasicTypes]]:
    return {
        key: map_api_uri_to_model_or_value(uri) for key, uri in context_json.items()
    }


def build_context_from_list(
    context_json: list[dict[str, str]],
) -> list[BasicTypes | Model | list[Model | BasicTypes]]:
    return [
        (
            getattr(
                map_api_uri_to_model_or_value(item["api_uri"]),
                item["property"],
                "invalid",
            )
            if "api_uri" in item
            else map_api_uri_to_model_or_value(item["value_uri"])
        )
        for item in context_json
    ]
