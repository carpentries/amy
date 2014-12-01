# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0004_auto_20141130_2224'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='attendance',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
    ]
