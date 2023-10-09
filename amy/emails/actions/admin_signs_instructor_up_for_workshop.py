from datetime import datetime
from typing import Any

from typing_extensions import Unpack

from emails.signals import admin_signs_instructor_up_for_workshop_signal
from emails.types import AdminSignsInstructorUpContext, AdminSignsInstructorUpKwargs
from emails.utils import immediate_action
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import Event, Person

from .base_action import BaseAction


class AdminSignsInstructorUpForWorkshopReceiver(BaseAction):
    signal = admin_signs_instructor_up_for_workshop_signal.signal_name

    def get_scheduled_at(self, **kwargs) -> datetime:
        return immediate_action()

    def get_context(
        self, **kwargs: Unpack[AdminSignsInstructorUpKwargs]
    ) -> AdminSignsInstructorUpContext:
        person = Person.objects.get(pk=kwargs["person_id"])
        event = Event.objects.get(pk=kwargs["event_id"])
        instructor_recruitment_signup = InstructorRecruitmentSignup.objects.get(
            pk=kwargs["instructor_recruitment_signup_id"]
        )
        return {
            "person": person,
            "event": event,
            "instructor_recruitment_signup": instructor_recruitment_signup,
        }

    def get_generic_relation_object(
        self, context: AdminSignsInstructorUpContext, **kwargs
    ) -> Any:
        return context["instructor_recruitment_signup"]

    def get_recipients(self, **kwargs) -> list[str]:
        person = Person.objects.get(pk=kwargs["person_id"])
        return [person.email] if person.email else []


admin_signs_instructor_up_for_workshop_receiver = (
    AdminSignsInstructorUpForWorkshopReceiver()
)
admin_signs_instructor_up_for_workshop_signal.connect(
    admin_signs_instructor_up_for_workshop_receiver
)
