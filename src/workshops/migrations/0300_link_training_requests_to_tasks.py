from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

# A task counts as a training task when it matches all three of these - the same
# conditions the training request list used to filter `Task` by before the link existed.
LEARNER_ROLE = "learner"
TTT_TAG = "TTT"

ACCEPTED = "a"


def link_training_requests_to_tasks(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Backfill `TrainingRequest.tasks` from the person shared by a request and a task.

    Nothing in the data says which request produced which task, so every training task a
    person holds is linked to every accepted request they hold. The relation is
    many-to-many precisely because that ambiguity is not resolvable: a person who
    re-applied and trained twice ends up with all four pairings, which is the honest
    answer.

    Only accepted requests are linked. Matching a trainee accepts their request, so any
    request matched through AMY is accepted; a pending or discarded request sharing a
    person with a training task is a request that some other route produced a task for,
    and `TrainingRequest.clean()` rejects a pending request with a task linked.
    """
    Task = apps.get_model("workshops", "Task")
    TrainingRequest = apps.get_model("workshops", "TrainingRequest")
    RequestTaskLink = TrainingRequest.tasks.through

    tasks_by_person: dict[int, list[int]] = {}
    training_tasks = Task.objects.filter(
        role__name=LEARNER_ROLE,
        event__tags__name=TTT_TAG,
        person__isnull=False,
    ).values_list("person_id", "pk")
    # An event may carry the TTT tag more than once via the join, hence the distinct().
    for person_id, task_id in training_tasks.distinct():
        tasks_by_person.setdefault(person_id, []).append(task_id)

    accepted_requests = TrainingRequest.objects.filter(
        state=ACCEPTED,
        person_id__in=tasks_by_person,
    ).values_list("person_id", "pk")

    links = [
        RequestTaskLink(trainingrequest_id=request_id, task_id=task_id)
        for person_id, request_id in accepted_requests
        for task_id in tasks_by_person[person_id]
    ]

    RequestTaskLink.objects.bulk_create(links, batch_size=500)


def unlink_training_requests_from_tasks(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Clear every link, which is the inverse of populating an empty relation.

    This also clears links made after the migration ran; there's no record of which ones
    this migration was responsible for.
    """
    TrainingRequest = apps.get_model("workshops", "TrainingRequest")
    TrainingRequest.tasks.through.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0299_trainingrequest_tasks"),
    ]

    operations = [
        migrations.RunPython(
            link_training_requests_to_tasks,
            reverse_code=unlink_training_requests_from_tasks,
        ),
    ]
