from django.core.exceptions import ValidationError

from workshops.models import Event, Person, Task


def raise_validation_error_if_no_learner_task(trainee: Person, event: Event) -> None:
    """Raises a ValidationError if trainee does not have a learner task for the event.
    Does nothing if trainee or event is None."""
    if not trainee or not event:
        return
    try:
        Task.objects.get(
            person=trainee,
            event=event,
            role__name="learner",
        )
        return
    except Task.DoesNotExist:
        msg = (
            "This progress cannot be created without a corresponding learner "
            f"task. Trainee {trainee} does not have a learner task for "
            f"event {event}."
        )
        raise ValidationError(msg)
