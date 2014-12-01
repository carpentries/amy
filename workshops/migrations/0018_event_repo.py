# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0017_auto_20141201_0839'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='repo',
            field=models.CharField(max_length=100, unique=True, null=True),
            preserve_default=True,
        ),
    ]
