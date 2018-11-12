# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def add_mentorship_badges(apps, schema_editor):
    Badge = apps.get_model('workshops', 'Badge')
    Badge.objects.create(name='mentor', title='Mentor', criteria='Mentor of Carpentry Instructors')
    Badge.objects.create(name='mentee', title='Mentee', criteria='Mentee in Carpentry Mentorship Program')


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0133_trainingrequest_options_helptexts'),
    ]

    operations = [
        migrations.RunPython(add_mentorship_badges),
    ]
