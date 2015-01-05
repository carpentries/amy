# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0027_auto_20141222_0144'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='published',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
