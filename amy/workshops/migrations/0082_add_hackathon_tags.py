# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def add_hackathon_tags(apps, schema_editor):
    """Add "hackathon tags."""
    Tag = apps.get_model('workshops', 'Tag')
    Tag.objects.create(
        name='hackathon',
        details='Event is a hackathon',
    )

class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0081_profileupdaterequest_notes'),
    ]

    operations = [
        migrations.RunPython(add_hackathon_tags),
        migrations.AlterField(
            model_name='event',
            name='tags',
            field=models.ManyToManyField(to='workshops.Tag'),
        ),
    ]
