from django.db import migrations


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("workshops", "0031_auto_20150720_0344"),
    ]

    operations = [
        migrations.RenameModel(
            old_name="Site",
            new_name="Host",
        ),
        migrations.RenameField(
            model_name="event",
            old_name="site",
            new_name="host",
        ),
    ]
