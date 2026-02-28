from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def add_hackathon_tags(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Add "hackathon tags."""
    Tag = apps.get_model("workshops", "Tag")
    Tag.objects.create(
        name="hackathon",
        details="Event is a hackathon",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0081_profileupdaterequest_notes"),
    ]

    operations = [
        migrations.RunPython(add_hackathon_tags),
        migrations.AlterField(
            model_name="event",
            name="tags",
            field=models.ManyToManyField(to="workshops.Tag"),
        ),
    ]
