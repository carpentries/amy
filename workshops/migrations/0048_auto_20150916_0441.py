# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0047_auto_20150916_0355'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='domains',
            field=models.ManyToManyField(blank=True, to='workshops.KnowledgeDomain'),
        ),
        migrations.AlterField(
            model_name='person',
            name='lessons',
            field=models.ManyToManyField(through='workshops.Qualification', blank=True, to='workshops.Lesson'),
        ),
    ]
