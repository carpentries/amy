# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0066_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='username',
            field=models.CharField(max_length=40, validators=[django.core.validators.RegexValidator('^[\\w\\.]+$', flags=256)], unique=True),
        ),
    ]
