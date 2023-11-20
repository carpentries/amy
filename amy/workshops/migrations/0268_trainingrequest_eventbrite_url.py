# Generated by Django 3.2.20 on 2023-11-08 16:59

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0267_alter_trainingrequest_default_for_text_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="trainingrequest",
            name="eventbrite_url",
            field=models.URLField(
                blank=True,
                default="",
                verbose_name="If you have already registered for an event through Eventbrite, enter the URL of that event.",
            ),
        ),
    ]
