# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def combine_names(apps, schema_editor):
    # We can't import the Person model directly as it may be a newer
    # version than this migration expects. We use the historical version.
    Person = apps.get_model('workshops', 'Person')
    for person in Person.objects.all():
        if person.middle:
            person.name = '{0.personal} {0.middle} {0.family}'.format(person)
        else:
            person.name = '{0.personal} {0.family}'.format(person)
        person.save()



class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0020_event_admin_fee'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='name',
            field=models.CharField(default='', max_length=100),
            preserve_default=False,
        ),
        migrations.RunPython(combine_names),
        migrations.RemoveField(
            model_name='person',
            name='family',
        ),
        migrations.RemoveField(
            model_name='person',
            name='middle',
        ),
        migrations.RemoveField(
            model_name='person',
            name='personal',
        ),
    ]
