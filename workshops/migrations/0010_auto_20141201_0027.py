# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0009_auto_20141201_0016'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='active',
            field=models.NullBooleanField(),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='person',
            name='airport',
            field=models.ForeignKey(to='workshops.Airport', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='person',
            name='gender',
            field=models.CharField(max_length=10, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='person',
            name='github',
            field=models.CharField(max_length=100, unique=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='person',
            name='twitter',
            field=models.CharField(max_length=100, unique=True, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='person',
            name='url',
            field=models.CharField(max_length=100, null=True),
            preserve_default=True,
        ),
    ]
