from datetime import datetime
from typing import Unpack

from src.emails.actions.base_action import BaseAction
from src.emails.schemas import ContextModel, SinglePropertyLinkModel, ToHeaderModel
from src.emails.signals import persons_merged_signal
from src.emails.types import PersonsMergedContext, PersonsMergedKwargs
from src.emails.utils import api_model_url, immediate_action
from src.workshops.models import Person


class PersonsMergedReceiver(BaseAction):
    signal = persons_merged_signal.signal_name

    def get_scheduled_at(self, **kwargs: Unpack[PersonsMergedKwargs]) -> datetime:
        return immediate_action()

    def get_context(self, **kwargs: Unpack[PersonsMergedKwargs]) -> PersonsMergedContext:
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

    def get_recipients(self, context: PersonsMergedContext, **kwargs: Unpack[PersonsMergedKwargs]) -> list[str]:
        person = context["person"]
        return [person.email] if person.email else []

    def get_recipients_context_json(
        self,
        context: PersonsMergedContext,
        **kwargs: Unpack[PersonsMergedKwargs],
    ) -> ToHeaderModel:
        return ToHeaderModel(
            [
                SinglePropertyLinkModel(
                    api_uri=api_model_url("person", context["person"].pk),
                    property="email",
                )
            ],
        )


persons_merged_receiver = PersonsMergedReceiver()
persons_merged_signal.connect(persons_merged_receiver)
