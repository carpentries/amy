from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def add_country_to_online_events(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Add an 'Online' country to all events tagged with 'online' tag."""
    Event = apps.get_model("workshops", "Event")

    Tag = apps.get_model("workshops", "Tag")
    online, _ = Tag.objects.get_or_create(
        name="online",
        defaults={"details": "Events taking place entirely online"},
    )

    # Oceanic Pole of Inaccessibility coordinates:
    # https://en.wikipedia.org/wiki/Pole_of_inaccessibility#Oceanic_pole_of_inaccessibility
    latitude = -48.876667
    longitude = -123.393333

    Event.objects.filter(country__isnull=True, tags__in=[online]).update(
        country="W3", latitude=latitude, longitude=longitude, venue="Internet"
    )


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0039_add_permission_groups"),
    ]

    operations = [
        migrations.RunPython(add_country_to_online_events),
    ]
