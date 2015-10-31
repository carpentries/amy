# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

import django
from django.db import models, migrations
from django.db.models import Q


def add_self_organized_host(apps, schema_editor):
    """Make new host: self-organized."""
    Host = apps.get_model('workshops', 'Host')
    Host.objects.create(domain='self-organized', fullname='self-organized',
                        country='W3')


def update_administrator_to_self_organized(apps, schema_editor):
    """Find all events that were self-organized and set administrator for them
    to be "self-organized"."""
    Host = apps.get_model('workshops', 'Host')
    self_org = Host.objects.get(fullname='self-organized')

    Event = apps.get_model('workshops', 'Event')
    Event.objects.filter(administrator__isnull=True) \
        .filter(
            Q(invoice_status='na-self-org') |
            Q(notes__contains='self-organized') |
            Q(notes__contains='self organized')
        ) \
        .update(administrator=self_org)


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0053_merge'),
    ]

    operations = [
        # some missing migration, totally healthy (changes only validators for the field)
        migrations.AlterField(
            model_name='event',
            name='url',
            field=models.CharField(validators=[django.core.validators.RegexValidator(re.compile('https?://github\\.com/(?P<name>[^/]+)/(?P<repo>[^/]+)/?', 32), inverse_match=True)], unique=True, max_length=100, help_text='Setting this and startdate "publishes" the event.<br />Use link to the event\'s website.', blank=True, null=True),
        ),

        migrations.RunPython(add_self_organized_host),
        migrations.RunPython(update_administrator_to_self_organized),
    ]
