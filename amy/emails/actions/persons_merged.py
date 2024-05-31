from datetime import datetime

from typing_extensions import Unpack

from emails.actions.base_action import BaseAction
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import persons_merged_signal
from emails.types import PersonsMergedContext, PersonsMergedKwargs
from emails.utils import api_model_url, immediate_action
from workshops.models import Person


class PersonsMergedReceiver(BaseAction):
    signal = persons_merged_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[PersonsMergedKwargs]) -> datetime:
        return immediate_action()

    def get_context(
        self, **kwargs: Unpack[PersonsMergedKwargs]
    ) -> PersonsMergedContext:
        person = Person.objects.get(pk=kwargs["selected_person_id"])
        return {
            "person": person,
        }

    def get_context_json(self, context: PersonsMergedContext) -> ContextModel:
        return ContextModel(
            {
                "person": api_model_url("person", context["person"].pk),
            },
        )

    def get_generic_relation_object(
        self, context: PersonsMergedContext, **kwargs: Unpack[PersonsMergedKwargs]
    ) -> Person:
        return context["person"]

    def get_recipients(
        self, context: PersonsMergedContext, **kwargs: Unpack[PersonsMergedKwargs]
    ) -> list[str]:
        person = context["person"]
        return [person.email] if person.email else []

    def get_recipients_context_json(
        self,
        context: PersonsMergedContext,
        **kwargs: Unpack[PersonsMergedKwargs],
    ) -> ToHeaderModel:
        return ToHeaderModel(
            [
                {
                    "api_uri": api_model_url("person", context["person"].pk),
                    "property": "email",
                },  # type: ignore
            ],
        )


persons_merged_receiver = PersonsMergedReceiver()
persons_merged_signal.connect(persons_merged_receiver)
