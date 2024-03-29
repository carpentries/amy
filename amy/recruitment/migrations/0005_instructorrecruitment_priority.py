# Generated by Django 3.2.13 on 2022-05-27 20:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recruitment', '0004_auto_20220526_0617'),
    ]

    operations = [
        migrations.AddField(
            model_name='instructorrecruitment',
            name='priority',
            field=models.IntegerField(blank=True, choices=[(1, 'Low'), (2, 'Medium'), (3, 'High')], help_text='If no priority is selected, automated priority will be calculated based on the days to start of the event.', null=True),
        ),
    ]
