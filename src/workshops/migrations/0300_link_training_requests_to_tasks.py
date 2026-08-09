from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

# A task counts as a training task when it matches all three of these - the same
# conditions as `Person.get_training_tasks()`.
LEARNER_ROLE = "learner"
TTT_TAG = "TTT"

ACCEPTED = "a"


def link_training_requests_to_tasks(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Backfill `TrainingRequest.task` for requests that can be paired with a training task
    beyond doubt.

    A person may hold several training requests (for example after re-applying) and several
    training tasks (after attending more than one training), and nothing in the data says
    which produced which. Rather than guess, this only links a person whose requests and
    tasks pair up unambiguously:

    * the person has exactly one training task, and
    * exactly one candidate request - where accepted requests, if there are any, are the
      only candidates, so a single accepted request still pairs up when the person's other
      requests were discarded or left pending.

    Everything else is left NULL to be handled by hand. `TrainingRequest.task` is a
    one-to-one field, so a wrong guess here could not be undone without knowing which
    pairing was wrong in the first place.
    """
    Task = apps.get_model("workshops", "Task")
    TrainingRequest = apps.get_model("workshops", "TrainingRequest")

    tasks_by_person: dict[int, list[int]] = {}
    training_tasks = Task.objects.filter(
        role__name=LEARNER_ROLE,
        event__tags__name=TTT_TAG,
        person__isnull=False,
    ).values_list("person_id", "pk")
    # An event may carry the TTT tag more than once via the join, hence the distinct().
    for person_id, task_id in training_tasks.distinct():
        tasks_by_person.setdefault(person_id, []).append(task_id)

    requests_by_person: dict[int, list[tuple[int, str]]] = {}
    for person_id, request_id, state in TrainingRequest.objects.filter(person_id__in=tasks_by_person).values_list(
        "person_id", "pk", "state"
    ):
        requests_by_person.setdefault(person_id, []).append((request_id, state))

    task_by_request: dict[int, int] = {}
    for person_id, task_ids in tasks_by_person.items():
        if len(task_ids) != 1:
            continue

        requests = requests_by_person.get(person_id, [])
        accepted = [request_id for request_id, state in requests if state == ACCEPTED]
        candidates = accepted or [request_id for request_id, _ in requests]

        if len(candidates) == 1:
            task_by_request[candidates[0]] = task_ids[0]

    to_update = list(TrainingRequest.objects.filter(pk__in=task_by_request))
    for training_request in to_update:
        training_request.task_id = task_by_request[training_request.pk]

    TrainingRequest.objects.bulk_update(to_update, ["task"], batch_size=500)


def unlink_training_requests_from_tasks(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Clear every link, which is the inverse of populating the column.

    This also clears links made after the migration ran; there's no record of which ones
    this migration was responsible for.
    """
    TrainingRequest = apps.get_model("workshops", "TrainingRequest")
    TrainingRequest.objects.filter(task__isnull=False).update(task=None)


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0299_trainingrequest_task"),
    ]

    operations = [
        migrations.RunPython(
            link_training_requests_to_tasks,
            reverse_code=unlink_training_requests_from_tasks,
        ),
    ]
