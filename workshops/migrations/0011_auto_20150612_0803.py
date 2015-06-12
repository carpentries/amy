# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0010_merge'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Skill',
            new_name='Lesson',
        ),
        migrations.RenameField(
            model_name='qualification',
            old_name='skill',
            new_name='lesson',
        ),
    ]
