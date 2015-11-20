# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
import re
import django_countries.fields


def add_address_to_online_events(apps, schema_editor):
    """Set Event.address if empty for online events."""
    Event = apps.get_model('workshops', 'Event')
    Tag = apps.get_model('workshops', 'Tag')
    online = Tag.objects.get(name='online')  # should be created via 0040_*

    Event.objects.filter(tags__in=[online]) \
                 .filter(models.Q(address=None) | models.Q(address='')) \
                 .update(address='Internet')
    Event.objects.filter(country='W3') \
                 .filter(models.Q(address=None) | models.Q(address='')) \
                 .update(address='Internet')


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0059_auto_20151109_1006'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='address',
            field=models.CharField(help_text='Required in order for this event to be "published".', max_length=255, blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='event',
            name='country',
            field=django_countries.fields.CountryField(help_text='Required in order for this event to be "published".<br />Use <b>Online</b> for online events.', null=True, max_length=2, blank=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='latitude',
            field=models.FloatField(help_text='Required in order for this event to be "published".', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='longitude',
            field=models.FloatField(help_text='Required in order for this event to be "published".', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='start',
            field=models.DateField(help_text='Required in order for this event to be "published".', null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='url',
            field=models.CharField(help_text='Required in order for this event to be "published".<br />Use link to the event\'s <b>website</b>, not repository.', max_length=100, blank=True, unique=True, validators=[django.core.validators.RegexValidator(re.compile('https?://github\\.com/(?P<name>[^/]+)/(?P<repo>[^/]+)/?', 32), inverse_match=True)], null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='venue',
            field=models.CharField(help_text='Required in order for this event to be "published".', max_length=255, blank=True, default=''),
        ),
        migrations.RunPython(add_address_to_online_events),
    ]
