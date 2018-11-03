# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0067_person_username_regexvalidator'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='instructors_post',
            field=models.URLField(verbose_name='Pre-workshop assessment survey for instructors', blank=True, default=''),
        ),
        migrations.AddField(
            model_name='event',
            name='instructors_pre',
            field=models.URLField(verbose_name='Pre-workshop assessment survey for instructors', blank=True, default=''),
        ),
        migrations.AddField(
            model_name='event',
            name='learners_longterm',
            field=models.URLField(verbose_name='Long-term assessment survey for learners', blank=True, default=''),
        ),
        migrations.AddField(
            model_name='event',
            name='learners_post',
            field=models.URLField(verbose_name='Post-workshop assessment survey for learners', blank=True, default=''),
        ),
        migrations.AddField(
            model_name='event',
            name='learners_pre',
            field=models.URLField(verbose_name='Pre-workshop assessment survey for learners', blank=True, default=''),
        ),
    ]
