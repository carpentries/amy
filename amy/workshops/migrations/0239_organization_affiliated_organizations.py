# Generated by Django 2.2.18 on 2021-03-27 18:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0238_task_seat_public'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='affiliated_organizations',
            field=models.ManyToManyField(to='workshops.Organization', blank=True),
        ),
    ]