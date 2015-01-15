# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0033_auto_20150106_0004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='active',
            field=models.NullBooleanField(help_text=b'Are we currently allowed to contact this person?'),
            preserve_default=True,
        ),
    ]
