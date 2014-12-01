# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0005_auto_20141130_2229'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='reg_key',
            field=models.CharField(max_length=20, null=True),
            preserve_default=True,
        ),
    ]
