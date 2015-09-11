# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def add_country_to_online_events(apps, schema_editor):
    """Add an 'Online' country to all events tagged with 'online' tag."""
    Event = apps.get_model('workshops', 'Event')

    Tag = apps.get_model('workshops', 'Tag')
    online, _ = Tag.objects.get_or_create(
        name='online',
        defaults={'details': 'Events taking place entirely online'},
    )

    Event.objects.filter(country__isnull=True, tags__in=[online]) \
         .update(country='W3')


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0039_add_permission_groups'),
    ]

    operations = [
        migrations.RunPython(add_country_to_online_events),
    ]
