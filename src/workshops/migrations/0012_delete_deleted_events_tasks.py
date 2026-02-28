from functools import partial

from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def drop_deleted_object(model: str, apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    m = apps.get_model("workshops", model)
    m.objects.filter(deleted=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0011_auto_20150611_0947"),
    ]

    operations = [
        migrations.RunPython(partial(drop_deleted_object, "Task")),
        migrations.RunPython(partial(drop_deleted_object, "Event")),
    ]
