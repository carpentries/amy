# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0016_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='site',
            field=models.ForeignKey(to='workshops.Site'),
        ),
    ]
