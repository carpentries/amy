# Generated by Django 4.2.19 on 2025-02-06 05:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("autoemails", "0019_alter_trigger_action"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="rqjob",
            name="trigger",
        ),
        migrations.RemoveField(
            model_name="trigger",
            name="template",
        ),
        migrations.DeleteModel(
            name="EmailTemplate",
        ),
        migrations.DeleteModel(
            name="RQJob",
        ),
        migrations.DeleteModel(
            name="Trigger",
        ),
    ]
