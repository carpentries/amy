# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0020_event_admin_fee'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='person',
            name='family',
        ),
        migrations.RemoveField(
            model_name='person',
            name='middle',
        ),
        migrations.RemoveField(
            model_name='person',
            name='personal',
        ),
        migrations.AddField(
            model_name='person',
            name='name',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
    ]
