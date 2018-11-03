# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def change_knowledgedomain_names(apps, schema_editor):
    '''Change "Psychology" → "Psychology/neuroscience".
    Change "Civil, mechanical, or chemical engineering" to
    "Civil, mechanical, chemical, or nuclear engineering".
    Add "Mathematics/statistics" and "High performance computing".'''
    KnowledgeDomain = apps.get_model('workshops', 'KnowledgeDomain')
    KnowledgeDomain.objects.filter(name='Psychology') \
                           .update(name='Psychology/neuroscience')
    KnowledgeDomain.objects \
        .filter(name='Civil, mechanical, or chemical engineering') \
        .update(name='Civil, mechanical, chemical, or nuclear engineering')
    KnowledgeDomain.objects.create(name='Mathematics/statistics')
    KnowledgeDomain.objects.create(name='High performance computing')


class Migration(migrations.Migration):
    dependencies = [
        ('workshops', '0024_merge'),
    ]

    operations = [
        migrations.RunPython(change_knowledgedomain_names)
    ]
