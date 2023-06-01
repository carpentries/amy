# Generated by elichad on 2023-05-31

from datetime import datetime

from django.db import migrations
from django.db.models import F, Value
from django.db.models.functions import Concat


def migrate_lesson_contributions_to_involvements(apps, schema_editor) -> None:
    """
    Forward step:
    Set all Lesson Contributions to have the GitHub Contribution involvement.
    This must occur before the renaming of Lesson Contribution to Get Involved.
    """
    TrainingProgress = apps.get_model("workshops", "TrainingProgress")
    Involvement = apps.get_model("trainings", "Involvement")

    involvement, _ = Involvement.objects.get_or_create(
        name="GitHub Contribution",
        defaults={
            "display_name": "Submitted a contribution to a Carpentries repository",
            "url_required": True,
            "date_required": True,
        },
    )
    updated_rows = TrainingProgress.objects.filter(
        requirement__name="Lesson Contribution"
    ).update(
        involvement_type=involvement,
        date=F("created_at"),
        notes=Concat(
            "notes", Value(f"\nMigrated from Lesson Contribution on {datetime.now()}\n")
        ),
    )
    print(f"Migrated {updated_rows} lesson contributions")


def migrate_involvements_to_lesson_contributions(apps, schema_editor) -> None:
    """
    Backward step:
    Un-link all involvements of type GitHub Contribution.
    This must occur after the renaming of Get Involved to Lesson Contribution.
    """
    TrainingProgress = apps.get_model("workshops", "TrainingProgress")

    updated_rows = TrainingProgress.objects.filter(
        involvement_type__name="GitHub Contribution"
    ).update(
        involvement_type=None,
        notes=Concat(
            "notes",
            Value(
                f"\nMigrated from GitHub Contribution involvement on {datetime.now()}\n"
            ),
        ),
    )
    print(f"Reverse-migrated {updated_rows} lesson contributions")


def rename_lesson_contribution_to_get_involved(apps, schema_editor) -> None:
    """
    Forward step.
    """
    TrainingRequirement = apps.get_model("workshops", "TrainingRequirement")

    try:
        requirement = TrainingRequirement.objects.get(name="Lesson Contribution")
        requirement.name = "Get Involved"
        requirement.url_required = False
        requirement.involvement_required = True
        requirement.save()
    except TrainingRequirement.DoesNotExist:
        pass


def rename_get_involved_to_lesson_contribution(apps, schema_editor) -> None:
    """
    Backward step.
    """
    TrainingRequirement = apps.get_model("workshops", "TrainingRequirement")

    try:
        requirement = TrainingRequirement.objects.get(name="Get Involved")
        requirement.name = "Lesson Contribution"
        requirement.url_required = True
        requirement.involvement_required = False
        requirement.save()
    except TrainingRequirement.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0260_add_involvement_types"),
    ]

    operations = [
        migrations.RunPython(
            migrate_lesson_contributions_to_involvements,
            migrate_involvements_to_lesson_contributions,
        ),
        migrations.RunPython(
            rename_lesson_contribution_to_get_involved,
            rename_get_involved_to_lesson_contribution,
        ),
    ]
