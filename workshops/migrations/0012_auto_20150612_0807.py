# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations

TRANSLATE_NAMES = {
    'Git': ['swc/git'],
    'Make': ['swc/make'],
    'Matlab': ['swc/matlab'],
    'Mercurial': ['swc/hg'],
    'Python': ['swc/python', 'dc/python'],
    'R': ['swc/r', 'dc/r'],
    'Regexp': ['swc/regexp'],
    'SQL': ['swc/sql', 'dc/sql'],
    'Subversion': ['swc/svn'],
    'Unix': ['swc/shell', 'dc/shell'],
    None: ['dc/spreadsheet', 'dc/cloud']
}

EXTRA_LEGACY_NAMES = ['MATLAB']


def add_new_lesson_names(apps, schema_editor):
    '''Add instances of Lesson named after lessons.'''
    Lesson = apps.get_model('workshops', 'Lesson')
    for (old_name, new_names) in TRANSLATE_NAMES.items():
        for name in new_names:
            Lesson.objects.create(name=name)


def fix_duplicate_names(apps, schema_editor):
    '''Fix references to lessons with case sensitivity in names.'''
    Lesson = apps.get_model('workshops', 'Lesson')
    Qualification = apps.get_model('workshops', 'Qualification')
    try:
        right_lesson = Lesson.objects.get(name='Matlab')
        wrong_lesson = Lesson.objects.get(name='MATLAB')
        Qualification.objects.filter(lesson=wrong_lesson) \
                             .update(lesson=right_lesson)
    except Lesson.DoesNotExist:
        pass


def replace_qualifications(apps, schema_editor):
    '''Add qualification entries with new lesson names and delete old ones.'''
    Lesson = apps.get_model('workshops', 'Lesson')
    Qualification = apps.get_model('workshops', 'Qualification')
    for q in Qualification.objects.all():
        old_name = q.lesson.name
        new_names = TRANSLATE_NAMES[old_name]
        for name in new_names:
            lesson = Lesson.objects.get(name=name)
            Qualification.objects.create(lesson=lesson,
                                         person=q.person)
        q.delete()


def remove_old_skill_names(apps, schema_editor):
    '''Remove legacy instances of Lesson named after skills.'''
    Lesson = apps.get_model('workshops', 'Lesson')
    for (old_name, new_names) in TRANSLATE_NAMES.items():
        if old_name:
            Lesson.objects.filter(name=old_name).delete()
    for old_name in EXTRA_LEGACY_NAMES:
        Lesson.objects.filter(name=old_name).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0011_auto_20150612_0803'),
    ]

    operations = [
        migrations.RunPython(add_new_lesson_names),
        migrations.RunPython(fix_duplicate_names),
        migrations.RunPython(replace_qualifications),
        migrations.RunPython(remove_old_skill_names)
    ]
