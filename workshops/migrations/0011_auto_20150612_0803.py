# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from functools import partial

from django.contrib.contenttypes.models import ContentType
from django.db import models, migrations


def remove_old_contentype(content_type, apps, schema_editor):
    """If we change model name, we need to remove its ContentType entry."""
    ContentType.objects.filter(app_label='workshops', model=content_type) \
                       .delete()


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0010_merge'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Skill',
            new_name='Lesson',
        ),
        migrations.RenameField(
            model_name='qualification',
            old_name='skill',
            new_name='lesson',
        ),
        migrations.RunPython(partial(remove_old_contentype, 'skill')),
    ]
