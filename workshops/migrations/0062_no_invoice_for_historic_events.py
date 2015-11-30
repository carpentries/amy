# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import date

from django.db import models, migrations

START_OF_MODERNITY = date(2014, 1, 1)


def no_invoice_for_historical_events(apps, schema_editor):
    """Set invoice status for historical (<2014) events."""
    Event = apps.get_model('workshops', 'Event')
    Event.objects \
        .filter(start__lt=START_OF_MODERNITY, invoice_status='unknown') \
        .update(invoice_status='ni-historic')


def mark_historical_events_completed(apps, schema_editor):
    """Set invoice status for historical (<2014) events."""
    Event = apps.get_model('workshops', 'Event')
    Event.objects \
        .filter(start__lt=date(2014, 1, 1), completed=False) \
        .update(completed=True)


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0061_merge'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='invoice_status',
            field=models.CharField(verbose_name='Invoice status', blank=True, default='unknown', choices=[('unknown', 'Unknown'), ('invoiced', 'Invoiced'), ('not-invoiced', 'Not invoiced'), ('ni-historic', 'Not invoiced for historical reasons'), ('ni-member', 'Not invoiced because of membership'), ('na-self-org', 'Not applicable because self-organized'), ('na-waiver', 'Not applicable because waiver granted'), ('na-other', 'Not applicable because other arrangements made')], max_length=40),
        ),
        migrations.RunPython(no_invoice_for_historical_events),
        migrations.RunPython(mark_historical_events_completed),
    ]
