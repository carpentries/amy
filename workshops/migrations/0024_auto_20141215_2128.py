# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0023_auto_20141215_1157'),
    ]

    operations = [
        migrations.CreateModel(
            name='TraineeStatus',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=40)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='trainee',
            name='complete',
        ),
        migrations.AddField(
            model_name='trainee',
            name='status',
            field=models.ForeignKey(default=4, to='workshops.TraineeStatus'),
            preserve_default=False,
        ),
    ]
