from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0006_merge"),
    ]

    operations = [
        migrations.RenameField(
            model_name="event",
            old_name="fee_paid",
            new_name="invoiced",
        ),
    ]
