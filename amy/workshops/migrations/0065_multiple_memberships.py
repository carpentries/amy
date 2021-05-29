# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0064_membership'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='host',
            name='membership',
        ),
        migrations.AddField(
            model_name='membership',
            name='host',
            # the default value of 1 here doesn't break anything, because
            # migrations 0064-0065 should be applied together
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, default=1, to='workshops.Host', null=True),
            preserve_default=False,
        ),
    ]
