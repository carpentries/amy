from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django_countries import countries


def migrate_to_2char_country_names(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Site = apps.get_model("workshops", "Site")
    Airport = apps.get_model("workshops", "Airport")

    # hard-coded list of mappings that fail to convert
    mapping = {"United-States": "US", "United-Kingdom": "GB", "European-Union": "EU", None: None}

    for site in Site.objects.all():
        country = site.country
        if country in mapping:
            site.country = mapping[country]
        else:
            country = country.replace("-", " ")
            site.country = countries.by_name(country)
        site.save()

    for airport in Airport.objects.all():
        country = airport.country
        if country in mapping:
            airport.country = mapping[country]
        else:
            country = country.replace("-", " ")
            airport.country = countries.by_name(country)
        airport.save()


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0006_merge"),
    ]

    operations = [
        migrations.RunPython(migrate_to_2char_country_names),
    ]
