from datetime import datetime

from typing_extensions import Unpack

from emails.actions.base_action import BaseAction
from emails.signals import instructor_badge_awarded_signal
from emails.types import InstructorBadgeAwardedContext, InstructorBadgeAwardedKwargs
from emails.utils import immediate_action
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


instructor_badge_awarded_receiver = InstructorBadgeAwardedReceiver()
instructor_badge_awarded_signal.connect(instructor_badge_awarded_receiver)
