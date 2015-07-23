# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0033_auto_20150721_0426'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='address',
            field=models.CharField(max_length=100, default='', blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='country',
            field=django_countries.fields.CountryField(max_length=2, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='latitude',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='longitude',
            field=models.FloatField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='venue',
            field=models.CharField(max_length=100, default='', blank=True),
        ),
    ]
