# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0035_auto_20150723_0958'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='contact',
            field=models.CharField(max_length=100, blank=True, default=''),
        ),
    ]
