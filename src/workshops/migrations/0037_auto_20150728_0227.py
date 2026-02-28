from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0036_event_contact"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="host",
            options={"ordering": ("domain",)},
        ),
    ]
