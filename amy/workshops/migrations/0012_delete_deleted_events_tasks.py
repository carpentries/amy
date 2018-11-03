# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from functools import partial

from django.db import models, migrations


def drop_deleted_object(model, apps, schema_editor):
    m = apps.get_model('workshops', model)
    m.objects.filter(deleted=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0011_auto_20150611_0947'),
    ]

    operations = [
        migrations.RunPython(partial(drop_deleted_object, 'Task')),
        migrations.RunPython(partial(drop_deleted_object, 'Event')),
    ]
