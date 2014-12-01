# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0015_auto_20141201_0751'),
    ]

    operations = [
        migrations.CreateModel(
            name='Award',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('awarded', models.DateField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=40)),
                ('title', models.CharField(max_length=40)),
                ('criteria', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='award',
            name='badge',
            field=models.ForeignKey(to='workshops.Badge'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='award',
            name='person',
            field=models.ForeignKey(to='workshops.Person'),
            preserve_default=True,
        ),
    ]
