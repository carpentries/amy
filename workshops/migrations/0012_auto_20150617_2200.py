# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0011_remove_event_published'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='url',
            field=models.CharField(unique=True, max_length=100, help_text='Setting this "publishes" the event.', null=True, blank=True),
        ),
    ]
