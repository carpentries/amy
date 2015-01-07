# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0034_auto_20150107_1200'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Project',
            new_name='Tag',
        ),
        migrations.RemoveField(
            model_name='event',
            name='project',
        ),
        migrations.AddField(
            model_name='event',
            name='tags',
            field=models.ManyToManyField(to='workshops.Tag'),
            preserve_default=True,
        ),
    ]
