# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0017_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='lessons',
            field=models.ManyToManyField(to='workshops.Lesson', through='workshops.Qualification'),
        ),
    ]
