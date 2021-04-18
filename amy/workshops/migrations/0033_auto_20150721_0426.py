# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0032_auto_20150721_0400'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='organizer',
            field=models.ForeignKey(related_name='administrator', help_text='Organization responsible for administrative work. Leave blank if self-organized.', blank=True, to='workshops.Host', on_delete=django.db.models.deletion.PROTECT, null=True),
        ),
        migrations.RenameField(
            model_name='event',
            old_name='organizer',
            new_name='administrator',
        ),
        migrations.AlterField(
            model_name='event',
            name='host',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, help_text='Organization hosting the event.', to='workshops.Host'),
        ),
    ]
