# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0007_migrate_countries_to_2char_iso31661'),
    ]

    operations = [
        migrations.AlterField(
            model_name='airport',
            name='country',
            field=django_countries.fields.CountryField(max_length=2),
        ),
        migrations.AlterField(
            model_name='site',
            name='country',
            field=django_countries.fields.CountryField(max_length=2, null=True),
        ),
    ]
