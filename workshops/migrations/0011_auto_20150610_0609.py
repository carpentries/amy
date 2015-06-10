# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0010_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='applicants',
            field=models.IntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='slots',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
