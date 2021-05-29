# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0029_auto_20150720_0258'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='attendance',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
