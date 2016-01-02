# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import workshops.models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0068_auto_20160102_1502'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventrequest',
            name='language',
            field=models.ForeignKey(to='workshops.Language', default=workshops.models.get_english, blank=True, verbose_name='What human language do you want the workshop to be run in?'),
        ),
    ]
