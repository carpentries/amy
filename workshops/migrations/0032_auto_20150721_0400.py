# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0031_auto_20150720_0344'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Site',
            new_name='Host',
        ),
        migrations.RenameField(
            model_name='event',
            old_name='site',
            new_name='host',
        ),
    ]
