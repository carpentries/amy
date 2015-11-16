# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from django.db import models, migrations


REPO_REGEX = re.compile(r'https?://github\.com/(?P<name>[^/]+)/'
                        r'(?P<repo>[^/]+)/?')
WEBSITE_REGEX = re.compile(r'https?://(?P<name>[^.]+)\.github\.'
                           r'(io|com)/(?P<repo>[^/]+)/?')
WEBSITE_FORMAT = 'https://{name}.github.io/{repo}/'


def website_url(url):
    """Return URL formatted as it was website URL.

    Website URL is as specified in WEBSITE_FORMAT.
    If it doesn't match, the original URL is returned."""
    try:
        # Try to match website regex first. This will result in all website
        # URLs always formatted in the same way.
        mo = (WEBSITE_REGEX.match(url)
              or REPO_REGEX.match(url))
        if not mo:
            return url

        return WEBSITE_FORMAT.format(**mo.groupdict())
    except (TypeError, KeyError):
        # TypeError: url is None
        # KeyError: mo.groupdict doesn't supply required names to format
        return url


def switch_events_to_website_urls(apps, schema_editor):
    """For every event in the DB, try to save it's URL as website URL.

    The rules are:
    * if current URL matches any known URL syntax, the resulting URL will be
      in format https://user.github.io/repository/ (got from event.website_url)
    * if it doesn't match, the URL won't change.
    """
    Event = apps.get_model('workshops', 'Event')

    for event in Event.objects.all():
        # Tricky: "apps.get_model" returns model without properties.
        # But we need event.website_url, which is a @property.  So I decided to
        # "copy" the Event.website_url into website_url() above.
        event.url = website_url(event.url)
        event.save()


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0051_auto_20150929_0847'),
    ]

    operations = [
        migrations.RunPython(switch_events_to_website_urls)
    ]
