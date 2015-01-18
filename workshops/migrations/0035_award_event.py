# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0034_auto_20150110_1131'),
    ]

    operations = [
        migrations.AddField(
            model_name='award',
            name='event',
            field=models.ForeignKey(blank=True, to='workshops.Event', null=True),
            preserve_default=True,
        ),
    ]
