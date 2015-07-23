# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from functools import partial

from django.db import models, migrations


def switch_host_to_tag(host_domain, new_host_domain, tag_name, tag_desc,
                       apps, schema_editor):
    Host = apps.get_model('workshops', 'Host')
    Event = apps.get_model('workshops', 'Event')
    Tag = apps.get_model('workshops', 'Tag')
    try:
        # get host that's about to be removed
        host = Host.objects.get(domain=host_domain)

        # get new host
        new_host = Host.objects.get(domain=new_host_domain)

        # get a replacement tag
        tag, _ = Tag.objects.get_or_create(name=tag_name,
                                           defaults={'details': tag_desc})

        events = Event.objects.filter(host=host).exclude(tags__in=[tag]) \
            .prefetch_related('tags')

        # add missing tag
        for event in events:
            event.tags.add(tag)

        # update to the new host
        Event.objects.filter(host=host) \
            .update(host=new_host)

        # nullify administrators, if any used the late host
        Event.objects.filter(administrator=host).update(administrator=None)

        # Drop old host
        # We can delete because the only protected deletion is at `Event.host`
        # and `Event.administrator` - both of which we updated.
        host.delete()

    except Host.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0034_auto_20150723_0431'),
    ]

    operations = [
        migrations.RunPython(partial(switch_host_to_tag, 'WISE',
                                     'software-carpentry.org', 'WiSE',
                                     'Women in Science and Engineering')),
        migrations.RunPython(partial(switch_host_to_tag, 'online',
                                     'software-carpentry.org', 'online',
                                     'Events taking place entirely online')),
    ]
