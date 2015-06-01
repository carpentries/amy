# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0007_auto_20150525_0906'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='award',
            unique_together=set([('person', 'badge')]),
        ),
    ]
