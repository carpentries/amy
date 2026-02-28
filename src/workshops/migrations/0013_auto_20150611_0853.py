from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0012_delete_deleted_events_tasks"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="event",
            name="deleted",
        ),
        migrations.RemoveField(
            model_name="task",
            name="deleted",
        ),
    ]
