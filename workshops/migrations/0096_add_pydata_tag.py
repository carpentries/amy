# -*- coding: utf-8 -*-
# Generated by Django 1.9.3 on 2016-06-05 16:52
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    def add_pydata_tag(apps, schema_editor):
        Tag = apps.get_model('workshops', 'Tag')
        Tag.objects.create(name='PyData', details='')

    dependencies = [
        ('workshops', '0095_add_training_request_model'),
    ]

    operations = [
        migrations.RunPython(add_pydata_tag),
    ]
