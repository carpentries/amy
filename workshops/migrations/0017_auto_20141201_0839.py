# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0016_auto_20141201_0807'),
    ]

    operations = [
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('slug', models.CharField(unique=True, max_length=10)),
                ('name', models.CharField(unique=True, max_length=40)),
                ('details', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='event',
            name='kind',
        ),
        migrations.AddField(
            model_name='event',
            name='project',
            field=models.ForeignKey(default=1, to='workshops.Project'),
            preserve_default=False,
        ),
    ]
