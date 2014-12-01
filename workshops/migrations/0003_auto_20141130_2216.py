# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0002_auto_20141130_2143'),
    ]

    operations = [
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start', models.DateField()),
                ('end', models.DateField()),
                ('slug', models.CharField(unique=True, max_length=100)),
                ('kind', models.CharField(max_length=10)),
                ('reg_key', models.CharField(max_length=20)),
                ('attendance', models.IntegerField()),
                ('site', models.ForeignKey(to='workshops.Site')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterField(
            model_name='airport',
            name='iata',
            field=models.CharField(unique=True, max_length=10),
            preserve_default=True,
        ),
    ]
