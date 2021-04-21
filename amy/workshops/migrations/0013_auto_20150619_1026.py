# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0012_auto_20150617_2200'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='start',
            field=models.DateField(blank=True, help_text='Setting this and url "publishes" the event.', null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='url',
            field=models.CharField(blank=True, max_length=100, help_text='Setting this and startdate "publishes" the event.', unique=True, null=True),
        ),
    ]
