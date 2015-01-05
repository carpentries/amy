# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0030_auto_20150104_2248'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='slug',
            field=models.CharField(max_length=100, null=True),
            preserve_default=True,
        ),
    ]
