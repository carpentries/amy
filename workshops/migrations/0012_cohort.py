# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0011_auto_20141201_0036'),
    ]

    operations = [
        migrations.CreateModel(
            name='Cohort',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start', models.DateField()),
                ('name', models.CharField(max_length=40)),
                ('active', models.BooleanField()),
                ('venue', models.ForeignKey(to='workshops.Site', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
