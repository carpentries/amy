# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0037_auto_20150728_0227'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='address',
            field=models.CharField(max_length=255, blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='event',
            name='contact',
            field=models.CharField(max_length=255, blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='event',
            name='venue',
            field=models.CharField(max_length=255, blank=True, default=''),
        ),
    ]
