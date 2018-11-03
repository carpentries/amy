# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0002_auto_20150219_1305'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='task',
            unique_together=set([('event', 'person', 'role')]),
        ),
    ]
