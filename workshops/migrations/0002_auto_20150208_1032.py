# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='notes',
            field=models.TextField(default='', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='person',
            name='gender',
            field=models.CharField(null=True, blank=True, max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='site',
            name='notes',
            field=models.TextField(default=''),
            preserve_default=True,
        ),
    ]
