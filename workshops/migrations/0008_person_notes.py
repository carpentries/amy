# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0007_auto_20150530_0537'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='notes',
            field=models.TextField(blank=True, default=''),
        ),
    ]
