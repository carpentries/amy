from typing import Any, TypedDict


class PersonsMergedKwargs(TypedDict):
    person_a_id: int
    person_b_id: int
    selected_person_id: int


def persons_merged_receiver(sender: Any, **kwargs: PersonsMergedKwargs) -> None:
    pass
