# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0057_merge'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='todoitem',
            options={'ordering': ['due', 'title']},
        ),
        migrations.AddField(
            model_name='person',
            name='is_active',
            field=models.BooleanField(default=False),
        ),
    ]
