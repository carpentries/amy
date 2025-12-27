from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def change_lesson_on_spreadsheets(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Change "dc/spreadsheet" → "dc/spreadsheets"."""
    Lesson = apps.get_model("workshops", "Lesson")
    Lesson.objects.filter(name="dc/spreadsheet").update(name="dc/spreadsheets")


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0021_add_knowledge_domains"),
    ]

    operations = [
        migrations.RunPython(change_lesson_on_spreadsheets),
    ]
