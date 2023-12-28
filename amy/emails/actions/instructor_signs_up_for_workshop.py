from datetime import datetime

from typing_extensions import Unpack

from emails.actions.base_action import BaseAction
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import instructor_signs_up_for_workshop_signal
from emails.types import InstructorSignupContext, InstructorSignupKwargs
from emails.utils import api_model_url, immediate_action
from recruitment.models import InstructorRecruitmentSignup
from workshops.models import Event, Person


class InstructorSignsUpForWorkshopReceiver(BaseAction):
    signal = instructor_signs_up_for_workshop_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[InstructorSignupKwargs]) -> datetime:
        return immediate_action()

    def get_context(
        self, **kwargs: Unpack[InstructorSignupKwargs]
    ) -> InstructorSignupContext:
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
        self, **kwargs: Unpack[InstructorSignupKwargs]
    ) -> ContextModel:
        return ContextModel(
            {
                "person": api_model_url("person", kwargs["person_id"]),
                "event": api_model_url("event", kwargs["event_id"]),
                "instructor_recruitment_signup": api_model_url(
                    "instructor_recruitment_signup",
                    kwargs["instructor_recruitment_signup_id"],
                ),
            },
        )

    def get_generic_relation_object(
        self, context: InstructorSignupContext, **kwargs: Unpack[InstructorSignupKwargs]
    ) -> InstructorRecruitmentSignup:
        return context["instructor_recruitment_signup"]

    def get_recipients(
        self, context: InstructorSignupContext, **kwargs: Unpack[InstructorSignupKwargs]
    ) -> list[str]:
        person = context["person"]
        return [person.email] if person.email else []

    def get_recipients_context_json(
        self, context: InstructorSignupContext, **kwargs: Unpack[InstructorSignupKwargs]
    ) -> ToHeaderModel:
        return ToHeaderModel(
            [
                {
                    "api_uri": api_model_url("person", context["person"].pk),
                    "property": "email",
                },
            ],  # type: ignore
        )


instructor_signs_up_for_workshop_receiver = InstructorSignsUpForWorkshopReceiver()
instructor_signs_up_for_workshop_signal.connect(
    instructor_signs_up_for_workshop_receiver
)
