# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0045_auto_20150907_1511'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventrequest',
            name='language',
            field=models.CharField(default='English', max_length=100, help_text='What human language you want the workshop to be run in?', blank=True, verbose_name='Workshop language'),
        ),
    ]
