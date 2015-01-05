# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0029_auto_20150104_2241'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='slug',
            field=models.CharField(max_length=100, unique=True, null=True),
            preserve_default=True,
        ),
    ]
