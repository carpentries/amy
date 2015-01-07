# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0033_auto_20150106_0004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='notes',
            field=models.TextField(default='', blank=True),
            preserve_default=True,
        ),
    ]
