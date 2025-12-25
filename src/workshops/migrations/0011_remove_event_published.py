from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0010_merge"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="event",
            name="published",
        ),
    ]
