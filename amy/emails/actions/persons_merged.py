from datetime import datetime

from typing_extensions import Unpack

from emails.actions.base_action import BaseAction
from emails.signals import persons_merged_signal
from emails.types import PersonsMergedContext, PersonsMergedKwargs
from emails.utils import immediate_action
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

    def get_generic_relation_object(
        self, context: PersonsMergedContext, **kwargs: Unpack[PersonsMergedKwargs]
    ) -> Person:
        return context["person"]

    def get_recipients(
        self, context: PersonsMergedContext, **kwargs: Unpack[PersonsMergedKwargs]
    ) -> list[str]:
        person = context["person"]
        return [person.email] if person.email else []


persons_merged_receiver = PersonsMergedReceiver()
persons_merged_signal.connect(persons_merged_receiver)
