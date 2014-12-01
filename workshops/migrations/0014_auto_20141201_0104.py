# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0013_auto_20141201_0048'),
    ]

    operations = [
        migrations.CreateModel(
            name='Trainee',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('complete', models.NullBooleanField()),
                ('cohort', models.ForeignKey(to='workshops.Cohort')),
                ('person', models.ForeignKey(to='workshops.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='cohort',
            name='qualifies',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
