from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import F

HPCC_TAG_NAME = "HPCC"
HPCC_TAG_DETAILS = "High Performance Computing Carpentry Workshop"
HPCC_TAG_PRIORITY = 4

HPCC_CURRICULA = {
    "hpcc": dict(
        carpentry="HPCC",
        name="High Performance Computing Carpentry",
        description="High Performance Computing Carpentry",
        website="https://hpcccarpentry.org/lessons",
        active=True,
        other=False,
        unknown=False,
        mix_match=False,
    ),
    "hpcc-other": dict(
        carpentry="HPCC",
        name="High Performance Computing Carpentry (other)",
        description="High Performance Computing Carpentry (other)",
        website="https://hpcccarpentry.org/lessons",
        active=True,
        other=True,
        unknown=False,
        mix_match=False,
    ),
}


def add_hpcc(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Tag = apps.get_model("workshops", "Tag")
    Curriculum = apps.get_model("workshops", "Curriculum")

    # Make space for HPCC at priority 4 (right after SWC=3) by bumping every
    # tag at priority 4 or higher down by one.
    Tag.objects.filter(priority__gte=HPCC_TAG_PRIORITY).update(priority=F("priority") + 1)
    Tag.objects.get_or_create(
        name=HPCC_TAG_NAME,
        defaults=dict(details=HPCC_TAG_DETAILS, priority=HPCC_TAG_PRIORITY),
    )

    for slug, defaults in HPCC_CURRICULA.items():
        Curriculum.objects.get_or_create(slug=slug, defaults=defaults)


def remove_hpcc(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    Tag = apps.get_model("workshops", "Tag")
    Curriculum = apps.get_model("workshops", "Curriculum")

    Curriculum.objects.filter(slug__in=HPCC_CURRICULA.keys()).delete()
    Tag.objects.filter(name=HPCC_TAG_NAME).delete()
    Tag.objects.filter(priority__gt=HPCC_TAG_PRIORITY).update(priority=F("priority") - 1)


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0293_alter_curriculum_carpentry_alter_event_country_and_more"),
    ]

    operations = [
        migrations.RunPython(add_hpcc, remove_hpcc),
    ]
