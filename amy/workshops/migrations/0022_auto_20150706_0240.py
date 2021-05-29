# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0021_add_knowledge_domains'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='reg_key',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='Eventbrite key'),
        ),
    ]
