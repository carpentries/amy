from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def remove_old_contentype(content_type: str, apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """If we change model name, we need to remove its ContentType entry."""
    ContentType.objects.filter(app_label="workshops", model=content_type).delete()


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("workshops", "0010_merge"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Skill",
            new_name="Lesson",
        ),
        migrations.RenameField(
            model_name="qualification",
            old_name="skill",
            new_name="lesson",
        ),
        migrations.RunPython(partial(remove_old_contentype, "skill")),
    ]
