# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0012_delete_deleted_events_tasks'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='event',
            name='deleted',
        ),
        migrations.RemoveField(
            model_name='task',
            name='deleted',
        ),
    ]
