from workshops.models import Person, TrainingProgress


def get_passed_or_last_progress(
    trainee: Person, requirement: str
) -> TrainingProgress | None:
    """Returns a recent progress, prioritising progress with a passed state.

    If there are one or more passed progresses, returns the most recent of those.
    Otherwise, returns the most recent progress of any state.
    If the trainee has no progresses for this requirement, returns None.
    """
    progresses = trainee.trainingprogress_set.filter(
        requirement__name=requirement
    ).order_by("-created_at")

    try:
        return progresses.filter(state="p")[0]
    except IndexError:
        return progresses.first()
