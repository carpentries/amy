# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0002_auto_20150219_1305'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='person',
            name='slug',
        ),
        migrations.AlterField(
            model_name='person',
            name='username',
            field=models.CharField(max_length=40, unique=True, blank=True),
            preserve_default=True,
        ),
    ]
