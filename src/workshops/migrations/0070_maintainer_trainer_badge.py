from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def add_maintainer_badge(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Badge = apps.get_model("workshops", "Badge")
    Badge.objects.create(
        name="maintainer", title="Maintainer", criteria="Maintainer of Software or Data Carpentry lesson"
    )
    Badge.objects.create(name="trainer", title="Trainer", criteria="Teaching instructor training workshops")


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0069_merge"),
    ]

    operations = [
        migrations.RunPython(add_maintainer_badge),
    ]
