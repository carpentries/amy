# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def add_maintainer_badge(apps, schema_editor):
    Badge = apps.get_model('workshops', 'Badge')
    Badge.objects.create(name='maintainer', title='Maintainer', criteria='Maintainer of Software or Data Carpentry lesson')
    Badge.objects.create(name='trainer', title='Trainer', criteria='Teaching instructor training workshops')


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0069_merge'),
    ]

    operations = [
        migrations.RunPython(add_maintainer_badge),
    ]
