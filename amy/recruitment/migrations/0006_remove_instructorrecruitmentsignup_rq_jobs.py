# Generated by Django 4.2.19 on 2025-02-06 05:10

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("recruitment", "0005_instructorrecruitment_priority"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="instructorrecruitmentsignup",
            name="rq_jobs",
        ),
    ]
