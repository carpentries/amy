# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0039_remove_tag_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='airport',
            field=models.ForeignKey(blank=True, to='workshops.Airport', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='person',
            name='github',
            field=models.CharField(max_length=40, unique=True, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='person',
            name='middle',
            field=models.CharField(max_length=100, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='person',
            name='slug',
            field=models.CharField(max_length=100, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='person',
            name='twitter',
            field=models.CharField(max_length=40, unique=True, null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='person',
            name='url',
            field=models.CharField(max_length=100, null=True, blank=True),
            preserve_default=True,
        ),
    ]
