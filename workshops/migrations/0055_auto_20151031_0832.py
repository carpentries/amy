# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0054_self_organized_host'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='administrator',
            field=models.ForeignKey(to='workshops.Host', help_text='Organization responsible for administrative work.', on_delete=django.db.models.deletion.PROTECT, null=True, related_name='administrator', blank=True),
        ),
    ]
