# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0019_event_organizer'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='admin_fee',
            field=models.DecimalField(default=0.0, max_digits=6, decimal_places=2),
            preserve_default=False,
        ),
    ]
