# Generated by Django 3.2.19 on 2023-05-17 16:53

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Involvement",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_updated_at", models.DateTimeField(auto_now=True, null=True)),
                ("archived_at", models.DateTimeField(blank=True, null=True)),
                (
                    "display_name",
                    models.CharField(
                        max_length=100,
                        help_text="This name will appear on community facing pages",
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        max_length=40,
                        help_text="A short descriptive name for internal use",
                        unique=True,
                    ),
                ),
                ("url_required", models.BooleanField(default=False)),
                ("date_required", models.BooleanField(default=True)),
                ("notes_required", models.BooleanField(default=False)),
            ],
            options={
                "ordering": ["name"],
            },
        ),
    ]
