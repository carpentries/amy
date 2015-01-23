# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0044_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='fee_paid',
            field=models.NullBooleanField(default=False),
            preserve_default=True,
        ),
    ]
