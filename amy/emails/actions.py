from typing import Any, TypedDict


class PersonsMergedKwargs(TypedDict):
    person_a: int
    person_b: int
    selected_person: int


def persons_merged_receiver(sender: Any, **kwargs: PersonsMergedKwargs) -> None:
    pass
