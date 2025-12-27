from typing import Any

from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import Q


def update_event_attendance_from_tasks(model: Any, event: Any) -> None:
    """Increase event.attendance if there's more learner tasks belonging to the
    event."""
    learners = event.task_set.filter(role__name="learner").count()
    model.objects.filter(pk=event.pk).filter(Q(attendance__lt=learners) | Q(attendance__isnull=True)).update(
        attendance=learners
    )


def update_attendance_for_historical_events(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Count attendance for events in the database."""
    Event = apps.get_model("workshops", "Event")
    for event in Event.objects.all():
        update_event_attendance_from_tasks(Event, event)


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0050_merge"),
    ]

    operations = [
        migrations.RunPython(update_attendance_for_historical_events),
    ]
