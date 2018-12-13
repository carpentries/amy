# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def add_stalled_unresponsive_tags(apps, schema_editor):
    """Add "stalled" and "unresponsive" tags."""
    Tag = apps.get_model('workshops', 'Tag')
    Tag.objects.create(
        name='stalled',
        details='Events with lost contact with the host or TTT events that '
                'aren\'t running.',
    )
    Tag.objects.create(
        name='unresponsive',
        details='Events whose hosts and/or organizers aren\'t going to send '
                'attendance data',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0061_merge'),
    ]

    operations = [
        migrations.RunPython(add_stalled_unresponsive_tags),
        migrations.AlterField(
            model_name='event',
            name='tags',
            field=models.ManyToManyField(help_text="<ul><li><i>stalled</i> — for events with lost contact with the host or TTT events that aren't running.</li><li><i>unresponsive</i> – for events whose hosts and/or organizers aren't going to send us attendance data.</li></ul>", to='workshops.Tag'),
        ),
    ]
