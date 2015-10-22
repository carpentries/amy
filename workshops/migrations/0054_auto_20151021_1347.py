# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0053_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='completed',
            field=models.BooleanField(help_text='Indicates that no more work is needed upon this event.', default=False),
        ),
    ]
