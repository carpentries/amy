# Generated by Django 3.2.19 on 2023-07-03 21:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('emails', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduledemail',
            name='generic_relation_content_type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='contenttypes.contenttype'),
        ),
        migrations.AddField(
            model_name='scheduledemail',
            name='generic_relation_pk',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
