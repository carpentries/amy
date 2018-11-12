# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0027_auto_20150714_1143'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='affiliation',
            field=models.CharField(default='', max_length=100, blank=True),
        ),
    ]
