# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0054_auto_20151021_1347'),
    ]

    operations = [
        migrations.CreateModel(
            name='TodoItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True, serialize=False)),
                ('completed', models.BooleanField(default=False)),
                ('title', models.CharField(max_length=100, default='')),
                ('due', models.DateField(blank=True, null=True)),
                ('additional', models.CharField(blank=True, max_length=255, default='')),
                ('event', models.ForeignKey(to='workshops.Event')),
            ],
        ),
    ]
