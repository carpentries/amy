# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0020_event_admin_fee'),
    ]

    operations = [
        migrations.AddField(
            model_name='site',
            name='notes',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
    ]
