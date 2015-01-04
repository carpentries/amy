# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0027_auto_20141222_0144'),
    ]

    operations = [
        migrations.CreateModel(
            name='Pending',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('notes', models.TextField(default=b'')),
                ('organizer', models.ForeignKey(related_name='pending_organizer', to='workshops.Site', null=True)),
                ('project', models.ForeignKey(to='workshops.Project')),
                ('site', models.ForeignKey(to='workshops.Site')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
