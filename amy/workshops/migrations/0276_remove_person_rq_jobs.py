# Generated by Django 4.2.19 on 2025-02-06 05:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("workshops", "0251_person_rq_jobs"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="person",
            name="rq_jobs",
        ),
    ]
