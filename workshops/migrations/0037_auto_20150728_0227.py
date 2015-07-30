# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0036_event_contact'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='host',
            options={'ordering': ('domain',)},
        ),
    ]
