# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0028_person_affiliation'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='lesson',
            options={'ordering': ['name']},
        ),
        migrations.AlterField(
            model_name='award',
            name='event',
            field=models.ForeignKey(to='workshops.Event', blank=True, null=True, on_delete=django.db.models.deletion.PROTECT),
        ),
    ]
