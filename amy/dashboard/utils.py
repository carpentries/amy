import re

from django.db.models import Q

from workshops.models import Person, TrainingProgress


def multiple_Q_icontains(term: str, *args: str) -> Q:
    q = Q()
    for arg in args:
        q |= Q(**{f"{arg}__icontains": term})
    return q


def tokenize(term: str) -> list[str]:
    return [v for v in re.split(r"\s+", term) if v]


def cross_multiple_Q_icontains(token1: str, token2: str, field1: str, field2: str) -> Q:
    q = (Q(**{f"{field1}__icontains": token1}) & Q(**{f"{field2}__icontains": token2})) | (
        Q(**{f"{field1}__icontains": token2}) & Q(**{f"{field2}__icontains": token1})
    )
    return q


def get_passed_or_last_progress(trainee: Person, requirement: str) -> TrainingProgress | None:
    """Returns a recent progress, prioritising progress with a passed state.

    If there are one or more passed progresses, returns the most recent of those.
    Otherwise, returns the most recent progress of any state.
    If the trainee has no progresses for this requirement, returns None.
    """
    progresses = trainee.trainingprogress_set.filter(requirement__name=requirement).order_by("-created_at")

    try:
        return progresses.filter(state="p")[0]
    except IndexError:
        return progresses.first()
