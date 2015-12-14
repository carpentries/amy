# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def change_instructor_badge_to_swc_instructor(apps, schemat_editor):
    """Get 'Instructor' badge, change it to 'Software Carpentry Instructor'."""
    Badge = apps.get_model('workshops', 'Badge')

    # it may not exist, for example in tests
    instructor, _ = Badge.objects.get_or_create(name='instructor')
    # new attributes:
    instructor.name = 'swc-instructor'
    instructor.title = 'Software Carpentry Instructor'
    instructor.criteria = 'Teaching at Software Carpentry workshops or online'
    instructor.save()


def add_dc_instructor_badge(apps, schemat_editor):
    """Add 'Data Carpentry Instructor' badge."""
    Badge = apps.get_model('workshops', 'Badge')
    Badge.objects.create(
        name='dc-instructor', title='Data Carpentry Instructor',
        criteria='Teaching at Data Carpentry workshops or online',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0063_merge'),
    ]

    operations = [
        migrations.RunPython(change_instructor_badge_to_swc_instructor),
        migrations.RunPython(add_dc_instructor_badge),
    ]
