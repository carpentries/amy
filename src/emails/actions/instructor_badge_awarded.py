import logging
from datetime import date, datetime
from io import BytesIO
from typing import Any, Unpack

import cairosvg
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpRequest

from src.emails.actions.base_action import BaseAction, BaseActionCancel, BaseActionUpdate
from src.emails.actions.base_strategy import run_strategy
from src.emails.controller import EmailController
from src.emails.models import ScheduledEmail, ScheduledEmailStatus
from src.emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from src.emails.signals import (
    INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
    Signal,
    instructor_badge_awarded_cancel_signal,
    instructor_badge_awarded_signal,
    instructor_badge_awarded_signal_sent,
    instructor_badge_awarded_update_signal,
)
from src.emails.types import (
    InstructorBadgeAwardedContext,
    InstructorBadgeAwardedKwargs,
    StrategyEnum,
)
from src.emails.utils import (
    api_model_url,
    immediate_action,
    log_condition_elements,
    scalar_value_none,
    scalar_value_url,
)
from src.workshops.models import Award, Person

logger = logging.getLogger("amy")


def instructor_badge_awarded_strategy(
    award: Award | None, person: Person, optional_award_pk: int | None = None
) -> StrategyEnum:
    logger.info(f"Running InstructorBadgeAwarded strategy for {award=}")

    award_pk = getattr(award, "pk", None)
    award_exists = award is not None and award_pk is not None
    instructor_award = award is not None and award.badge.name == "instructor"

    log_condition_elements(
        award=award,
        award_pk=award_pk,
        optional_award_pk=optional_award_pk,
        award_exists=award_exists,
        instructor_award=instructor_award,
    )

    email_should_exist = award_exists and instructor_award
    logger.debug(f"{email_should_exist=}")

    ct = ContentType.objects.get_for_model(Award)
    has_email_scheduled = ScheduledEmail.objects.filter(
        generic_relation_content_type=ct,
        generic_relation_pk=optional_award_pk or award_pk,
        template__signal=INSTRUCTOR_BADGE_AWARDED_SIGNAL_NAME,
        state=ScheduledEmailStatus.SCHEDULED,
    ).exists()
    logger.debug(f"{has_email_scheduled=}")

    if not has_email_scheduled and email_should_exist:
        result = StrategyEnum.CREATE
    elif has_email_scheduled and not email_should_exist:
        result = StrategyEnum.CANCEL
    elif has_email_scheduled and email_should_exist:
        result = StrategyEnum.UPDATE
    else:
        result = StrategyEnum.NOOP

    logger.debug(f"InstructorBadgeAwarded strategy {result=}")
    return result


def run_instructor_badge_awarded_strategy(
    strategy: StrategyEnum, request: HttpRequest, person: Person, **kwargs: Any
) -> None:
    signal_mapping: dict[StrategyEnum, Signal | None] = {
        StrategyEnum.CREATE: instructor_badge_awarded_signal,
        StrategyEnum.UPDATE: instructor_badge_awarded_update_signal,
        StrategyEnum.CANCEL: instructor_badge_awarded_cancel_signal,
        StrategyEnum.NOOP: None,
    }
    return run_strategy(
        strategy,
        signal_mapping,
        request,
        sender=person,
        **kwargs,
    )


def get_scheduled_at(**kwargs: Unpack[InstructorBadgeAwardedKwargs]) -> datetime:
    return immediate_action()


def get_context(
    **kwargs: Unpack[InstructorBadgeAwardedKwargs],
) -> InstructorBadgeAwardedContext:
    person = Person.objects.get(pk=kwargs["person_id"])
    award = Award.objects.filter(pk=kwargs["award_id"]).first()
    return {
        "person": person,
        "award": award,
        "award_id": kwargs["award_id"],
    }


def get_context_json(context: InstructorBadgeAwardedContext) -> ContextModel:
    award = context["award"]
    return ContextModel(
        {
            "person": api_model_url("person", context["person"].pk),
            "award": api_model_url("award", award.pk) if award else scalar_value_none(),
            "award_id": scalar_value_url("int", f"{context['award_id']}"),
        },
    )


def get_generic_relation_object(
    context: InstructorBadgeAwardedContext,
    **kwargs: Unpack[InstructorBadgeAwardedKwargs],
) -> Award:
    # When removing award, this will be None.
    return context["award"]  # type: ignore


def get_recipients(
    context: InstructorBadgeAwardedContext,
    **kwargs: Unpack[InstructorBadgeAwardedKwargs],
) -> list[str]:
    person = context["person"]
    return [person.email] if person.email else []


def get_recipients_context_json(
    context: InstructorBadgeAwardedContext,
    **kwargs: Unpack[InstructorBadgeAwardedKwargs],
) -> ToHeaderModel:
    return ToHeaderModel(
        [
            SinglePropertyLinkModel(
                api_uri=api_model_url("person", context["person"].pk),
                property="email",
            )
        ],
    )


class InstructorBadgeAwardedReceiver(BaseAction):
    signal = instructor_badge_awarded_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]) -> InstructorBadgeAwardedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorBadgeAwardedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> Award:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)

    def __call__(self, sender: Any, *args: Any, **kwargs: Any) -> ScheduledEmail | None:
        scheduled_email = super().__call__(sender, *args, **kwargs)
        instructor_badge_awarded_signal_sent.send(sender=scheduled_email)
        return scheduled_email


class InstructorBadgeAwardedUpdateReceiver(BaseActionUpdate):
    signal = instructor_badge_awarded_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]) -> datetime:
        return get_scheduled_at(**kwargs)

    def get_context(self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]) -> InstructorBadgeAwardedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorBadgeAwardedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_object(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> Award:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> list[str]:
        return get_recipients(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


class InstructorBadgeAwardedCancelReceiver(BaseActionCancel):
    signal = instructor_badge_awarded_signal.signal_name

    def get_context(self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]) -> InstructorBadgeAwardedContext:
        return get_context(**kwargs)

    def get_context_json(self, context: InstructorBadgeAwardedContext) -> ContextModel:
        return get_context_json(context)

    def get_generic_relation_content_type(
        self, context: InstructorBadgeAwardedContext, generic_relation_obj: Any
    ) -> ContentType:
        return ContentType.objects.get_for_model(Award)

    def get_generic_relation_pk(self, context: InstructorBadgeAwardedContext, generic_relation_obj: Any) -> int | Any:
        return context["award_id"]

    def get_generic_relation_object(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> Award:
        return get_generic_relation_object(context, **kwargs)

    def get_recipients_context_json(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> ToHeaderModel:
        return get_recipients_context_json(context, **kwargs)


instructor_badge_awarded_receiver = InstructorBadgeAwardedReceiver()
instructor_badge_awarded_signal.connect(instructor_badge_awarded_receiver)

instructor_badge_awarded_update_receiver = InstructorBadgeAwardedUpdateReceiver()
instructor_badge_awarded_update_signal.connect(instructor_badge_awarded_update_receiver)

instructor_badge_awarded_cancel_receiver = InstructorBadgeAwardedCancelReceiver()
instructor_badge_awarded_cancel_signal.connect(instructor_badge_awarded_cancel_receiver)


def read_binary_file_and_replace_values(file_path: str, replacements: dict[bytes, bytes]) -> bytes:
    with open(file_path, "rb") as f:
        byte_content = f.read()
        for key, value in replacements.items():
            byte_content = byte_content.replace(key, value)
    return byte_content


def generate_pdf(svg_file: bytes) -> bytes:
    file_obj = BytesIO()
    cairosvg.svg2pdf(svg_file, write_to=file_obj, dpi=90)  # type: ignore[no-untyped-call]
    file_obj.seek(0)
    return file_obj.read()


def generate_and_attach_certificate_pdf(sender: ScheduledEmail | None, *args: Any, **kwargs: Any) -> None:
    logger.info(f"Generating certificate PDF strategy for {sender=}")

    # `sender` is None also in case when the feature flag `EMAIL_MODULE` is not enabled.
    # Unfortunately, it's not possible to check for feature flags in this function, because `request`
    # kwarg is missing.

    if sender is None:
        logger.error(f"Failed to generate and attach certificate: sender is not a ScheduledEmail (it's {sender})")
        return

    if not isinstance(sender.generic_relation, Award):
        logger.error(
            "Failed to generate and attach certificate: related object is not an Award "
            f"(it's {sender.generic_relation})"
        )
        return

    # Parameters for the SVG file
    full_name = sender.generic_relation.person.full_name
    award_date = date.strftime(sender.generic_relation.awarded, r"%d %B %Y")
    signature = settings.CERTIFICATE_SIGNATURE
    file_path = settings.APPS_DIR / "templates" / "certificates" / "carpentries-instructor.svg"

    # Prepare SVG file in memory.
    svg_file = read_binary_file_and_replace_values(
        file_path=str(file_path),
        replacements={
            b"{{name}}": bytes(full_name, encoding="utf-8"),
            b"{{date}}": bytes(award_date, encoding="utf-8"),
            b"{{signature}}": bytes(signature, encoding="utf-8"),
        },
    )

    # Generate PDF out of SVG (in memory).
    content = generate_pdf(svg_file)

    # Attach to email.
    EmailController.add_attachment(sender, filename="certificate.pdf", content=content)


instructor_badge_awarded_signal_sent.connect(generate_and_attach_certificate_pdf)
