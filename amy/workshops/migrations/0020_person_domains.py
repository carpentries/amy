# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0019_knowledgedomain'),
    ]

    operations = [
        migrations.AddField(
            model_name='person',
            name='domains',
            field=models.ManyToManyField(to='workshops.KnowledgeDomain'),
        ),
    ]
