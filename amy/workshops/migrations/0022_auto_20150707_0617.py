# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def change_lesson_on_spreadsheets(apps, schema_editor):
    '''Change "dc/spreadsheet" → "dc/spreadsheets".'''
    Lesson = apps.get_model('workshops', 'Lesson')
    Lesson.objects.filter(name='dc/spreadsheet').update(name='dc/spreadsheets')


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0021_add_knowledge_domains'),
    ]

    operations = [
        migrations.RunPython(change_lesson_on_spreadsheets),
    ]
