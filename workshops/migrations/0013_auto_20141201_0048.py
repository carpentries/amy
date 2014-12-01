# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0012_cohort'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cohort',
            name='active',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
