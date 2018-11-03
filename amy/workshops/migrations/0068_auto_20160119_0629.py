# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0067_person_username_regexvalidator'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='occupation',
            field=models.CharField(max_length=100, blank=True, verbose_name='Current occupation/career stage', default=''),
        ),
        migrations.AddField(
            model_name='person',
            name='orcid',
            field=models.CharField(max_length=100, blank=True, verbose_name='ORCID ID', default=''),
        ),
    ]
