# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0022_auto_20150706_0240'),
    ]

    operations = [
        migrations.AlterField(
            model_name='airport',
            name='fullname',
            field=models.CharField(max_length=100, verbose_name='Airport name', unique=True),
        ),
        migrations.AlterField(
            model_name='airport',
            name='iata',
            field=models.CharField(max_length=10, help_text='<a href="https://www.world-airport-codes.com/">Look up code</a>', unique=True, verbose_name='IATA code'),
        ),
    ]
