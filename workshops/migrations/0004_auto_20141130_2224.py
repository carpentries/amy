# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0003_auto_20141130_2216'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='country',
            field=models.CharField(max_length=100, null=True),
            preserve_default=True,
        ),
    ]
