# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def migrate_invoiced(apps, schema_editor):
    """Migrate `invoiced` bool field into `invoice_status` text field."""
    Event = apps.get_model('workshops', 'Event')

    # null → 'unknown'
    Event.objects.filter(invoiced__isnull=True) \
        .update(invoice_status='unknown')
    # true → 'invoiced'
    Event.objects.filter(invoiced=True) \
        .update(invoice_status='invoiced')
    # false → 'invoiced'
    Event.objects.filter(invoiced=False) \
        .update(invoice_status='not-invoiced')


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0039_add_permission_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='invoice_status',
            field=models.CharField(verbose_name='Invoice status', max_length=40, default='unknown', blank=True, choices=[('unknown', 'Unknown'), ('invoiced', 'Invoiced'), ('not-invoiced', 'Not invoiced'), ('na-self-org', 'Not applicable because self-organized'), ('na-waiver', 'Not applicable because waiver granted'), ('na-other', 'Not applicable because other arrangements made')]),
        ),
        migrations.RunPython(migrate_invoiced),
        migrations.RemoveField(
            model_name='event',
            name='invoiced',
        ),
    ]
