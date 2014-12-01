# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0010_auto_20141201_0027'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('role', models.CharField(max_length=40)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('event', models.ForeignKey(to='workshops.Event')),
                ('person', models.ForeignKey(to='workshops.Person')),
                ('role', models.ForeignKey(to='workshops.Role')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='person',
            name='github',
            field=models.CharField(max_length=40, unique=True, null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='person',
            name='twitter',
            field=models.CharField(max_length=40, unique=True, null=True),
            preserve_default=True,
        ),
    ]
