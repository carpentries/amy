# Generated by Django 3.2.20 on 2023-08-22 16:33

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0263_remove_workshoprequest_number_attendees"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="trainingprogress",
            constraint=models.UniqueConstraint(
                fields=("trainee", "event"), name="unique_trainee_at_event"
            ),
        ),
    ]
