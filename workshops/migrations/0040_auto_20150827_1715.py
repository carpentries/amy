# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def add_academic_levels(apps, schema_editor):
    AcademicLevel = apps.get_model('workshops', 'AcademicLevel')
    names = [
        'Undergraduate or below',
        'Graduate',
        'Post-doctorate',
        'Faculty',
        'Industry',
        'Don\'t know yet',
    ]
    for name in names:
        AcademicLevel.objects.create(name=name)


def add_comp_exp_levels(apps, schema_editor):
    ComputingExperienceLevel = apps.get_model('workshops',
                                              'ComputingExperienceLevel')
    names = [
        'Novice (uses a spreadsheet for data analysis rather than writing code)',
        'Intermediate (can write a few lines of code for personal use)',
        'Proficient (writes multi-page programs which may be shared with others)',
        'Don\'t know yet',
    ]
    for name in names:
        ComputingExperienceLevel.objects.create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0039_academiclevel_computingexperiencelevel_eventrequest'),
    ]

    operations = [
        migrations.RunPython(add_academic_levels),
        migrations.RunPython(add_comp_exp_levels),
    ]
