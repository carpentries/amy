# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def copy_project_to_tags(apps, schema_editor):
    Event = apps.get_model('workshops', 'Event')
    for event in Event.objects.all().exclude(project=None):
        tag = event.project
        print('add {} to {}'.format(tag, event))
        event.tags.add(tag)
        event.save()


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0034_auto_20150107_1200'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Project',
            new_name='Tag',
        ),
        migrations.AddField(
            model_name='event',
            name='tags',
            field=models.ManyToManyField(to='workshops.Tag'),
            preserve_default=True,
        ),
        migrations.RunPython(copy_project_to_tags),
        migrations.RemoveField(
            model_name='event',
            name='project',
        ),
    ]
