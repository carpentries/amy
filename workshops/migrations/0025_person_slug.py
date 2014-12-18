# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0024_auto_20141215_2128'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='slug',
            field=models.CharField(max_length=100, null=True),
            preserve_default=True,
        ),
    ]
