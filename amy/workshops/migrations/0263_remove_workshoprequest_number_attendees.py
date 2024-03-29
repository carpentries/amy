# Generated by Django 3.2.20 on 2023-08-15 11:23

from django.db import migrations, models

ATTENDEES_NUMBER_CHOICES = (
    ("10-40", "10-40 (one room, two instructors)"),
    ("40-80", "40-80 (two rooms, four instructors)"),
    ("80-120", "80-120 (three rooms, six instructors)"),
)


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0262_alter_trainingrequest_training_completion_agreement"),
    ]

    operations = [
        migrations.AlterField(
            model_name="workshoprequest",
            name="number_attendees",
            field=models.CharField(
                max_length=15,
                choices=ATTENDEES_NUMBER_CHOICES,
                blank=False,
                null=False,
                default="",  # must have a default for migration to be reversible
                verbose_name="Anticipated number of attendees",
                help_text="These recommendations are for in-person workshops. "
                "This number doesn't need to be precise, but will help us "
                "decide how many instructors your workshop will need. "
                "Each workshop must have at least two instructors.<br>"
                "For online Carpentries workshops, we recommend a maximum of "
                "20 learners per class. If your workshop attendance will "
                "exceed 20 learners please be sure to include a note in the "
                "comments section below. ",
            ),
        ),
        migrations.RemoveField(
            model_name="workshoprequest",
            name="number_attendees",
        ),
    ]
