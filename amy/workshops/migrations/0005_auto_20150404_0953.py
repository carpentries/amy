# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0004_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='groups',
            field=models.ManyToManyField(help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', blank=True, to='auth.Group', related_name='user_set', related_query_name='user', verbose_name='groups'),
        ),
        migrations.AlterField(
            model_name='person',
            name='last_login',
            field=models.DateTimeField(blank=True, null=True, verbose_name='last login'),
        ),
    ]
