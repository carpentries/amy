from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def add_mentorship_badges(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Badge = apps.get_model("workshops", "Badge")
    Badge.objects.create(name="mentor", title="Mentor", criteria="Mentor of Carpentry Instructors")
    Badge.objects.create(name="mentee", title="Mentee", criteria="Mentee in Carpentry Mentorship Program")


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0133_trainingrequest_options_helptexts"),
    ]

    operations = [
        migrations.RunPython(add_mentorship_badges),
    ]
