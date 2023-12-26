from datetime import datetime

from typing_extensions import Unpack

from emails.actions.base_action import BaseAction
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import instructor_badge_awarded_signal
from emails.types import InstructorBadgeAwardedContext, InstructorBadgeAwardedKwargs
from emails.utils import api_model_url, immediate_action
from workshops.models import Award, Person


class InstructorBadgeAwardedReceiver(BaseAction):
    signal = instructor_badge_awarded_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]
    ) -> datetime:
        return immediate_action()

    def get_context(
        self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]
    ) -> InstructorBadgeAwardedContext:
        person = Person.objects.get(pk=kwargs["person_id"])
        award = Award.objects.get(pk=kwargs["award_id"])
        return {
            "person": person,
            "award": award,
        }

    def get_context_json(
        self, **kwargs: Unpack[InstructorBadgeAwardedKwargs]
    ) -> ContextModel:
        return ContextModel(
            {
                "person": api_model_url("person", kwargs["person_id"]),
                "award": api_model_url("award", kwargs["award_id"]),
            },  # type: ignore
        )

    def get_generic_relation_object(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> Award:
        return context["award"]

    def get_recipients(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> list[str]:
        person = context["person"]
        return [person.email] if person.email else []

    def get_recipients_context_json(
        self,
        context: InstructorBadgeAwardedContext,
        **kwargs: Unpack[InstructorBadgeAwardedKwargs],
    ) -> ToHeaderModel:
        return ToHeaderModel(
            [
                {
                    "api_uri": api_model_url("person", context["person"].pk),
                    "property": "email",
                },
            ],  # type: ignore
        )


instructor_badge_awarded_receiver = InstructorBadgeAwardedReceiver()
instructor_badge_awarded_signal.connect(instructor_badge_awarded_receiver)
