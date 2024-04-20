from datetime import datetime

from typing_extensions import Unpack

from emails.actions.base_action import BaseAction
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import admin_signs_instructor_up_for_workshop_signal
from emails.types import AdminSignsInstructorUpContext, AdminSignsInstructorUpKwargs
from emails.utils import api_model_url, immediate_action
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import Event, Person


class AdminSignsInstructorUpForWorkshopReceiver(BaseAction):
    signal = admin_signs_instructor_up_for_workshop_signal.signal_name

    def get_scheduled_at(
        self, **kwargs: Unpack[AdminSignsInstructorUpKwargs]
    ) -> datetime:
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

    def get_context_json(
        self, **kwargs: Unpack[AdminSignsInstructorUpKwargs]
    ) -> ContextModel:
        return ContextModel(
            {
                "person": api_model_url("person", kwargs["person_id"]),
                "event": api_model_url("event", kwargs["event_id"]),
                "instructor_recruitment_signup": api_model_url(
                    "instructorrecruitmentsignup",
                    kwargs["instructor_recruitment_signup_id"],
                ),
            },
        )

    def get_generic_relation_object(
        self,
        context: AdminSignsInstructorUpContext,
        **kwargs: Unpack[AdminSignsInstructorUpKwargs],
    ) -> InstructorRecruitmentSignup:
        return context["instructor_recruitment_signup"]

    def get_recipients(
        self,
        context: AdminSignsInstructorUpContext,
        **kwargs: Unpack[AdminSignsInstructorUpKwargs],
    ) -> list[str]:
        person = context["person"]
        return [person.email] if person.email else []

    def get_recipients_context_json(
        self,
        context: AdminSignsInstructorUpContext,
        **kwargs: Unpack[AdminSignsInstructorUpKwargs],
    ) -> ToHeaderModel:
        return ToHeaderModel(
            [
                {
                    "api_uri": api_model_url("person", context["person"].pk),
                    "property": "email",
                },
            ],  # type: ignore
        )


admin_signs_instructor_up_for_workshop_receiver = (
    AdminSignsInstructorUpForWorkshopReceiver()
)
admin_signs_instructor_up_for_workshop_signal.connect(
    admin_signs_instructor_up_for_workshop_receiver
)
