# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0044_merge'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='person',
            name='active',
        ),
        migrations.AddField(
            model_name='person',
            name='may_contact',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
