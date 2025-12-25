from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0053_merge"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="completed",
            field=models.BooleanField(
                help_text="Indicates that no more work is needed upon this event.", default=False
            ),
        ),
    ]
