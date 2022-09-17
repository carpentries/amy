# Generated by Django 3.2.13 on 2022-05-26 07:23

from django.db import migrations, models
import django_better_admin_arrayfield.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('communityroles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='communityrole',
            name='custom_keys',
            field=models.JSONField(blank=True, null=True, default=str),
        ),
        migrations.AddField(
            model_name='communityroleconfig',
            name='custom_key_labels',
            field=django_better_admin_arrayfield.models.fields.ArrayField(base_field=models.CharField(max_length=150), blank=True, default=list, help_text='Labels to be used for custom text fields in community roles.', size=None),
        ),
    ]