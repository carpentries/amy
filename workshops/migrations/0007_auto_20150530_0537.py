# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0006_merge'),
    ]

    operations = [
        migrations.RenameField(
            model_name='event',
            old_name='fee_paid',
            new_name='invoiced',
        ),
    ]
