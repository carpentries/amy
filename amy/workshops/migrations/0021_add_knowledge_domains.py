# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

DOMAINS = [
    'Space sciences',
    'Planetary sciences (geology, climatology, oceanography, etc.)',
    'Physics',
    'Chemistry',
    'Organismal biology (ecology, botany, zoology, microbiology)',
    'Genetics, genomics, bioinformatics',
    'Medicine',
    'Civil, mechanical, or chemical engineering',
    'Computer science/electrical engineering',
    'Economics/business',
    'Social sciences',
    'Psychology',
    'Humanities',
    'Library and information science',
    'Education',
]


def add_knowledge_domains(apps, schema_editor):
    '''Add instances of KnowledgeDomains.'''
    KnowledgeDomain = apps.get_model('workshops', 'KnowledgeDomain')
    for domain in DOMAINS:
        KnowledgeDomain.objects.create(name=domain)


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0020_person_domains'),
    ]

    operations = [
        migrations.RunPython(add_knowledge_domains),
    ]
