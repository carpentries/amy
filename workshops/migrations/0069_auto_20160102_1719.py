# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import workshops.models


def migrate_language(apps, schema_editor):
    """Convert EventRequest.language string to key"""
    EventRequest = apps.get_model('workshops', 'EventRequest')
    Language = apps.get_model('workshops', 'Language')
    for request in EventRequest.objects.all():
        languages = Language.objects.filter(name__icontains=request.language)
        count = languages.count()
        if count == 0:
            raise ValueError('no languages matching {} (for {})'.format(
                request.language, request))
        if count > 1:
            raise ValueError(
                'multiple languages matching {} (for {}): {}'.format(
                    request.language, request, list(languages)))
        language = languages[0]
        request.language_new = language
        request.save()


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0068_auto_20160102_1502'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventrequest',
            name='language_new',
            field=models.ForeignKey(to='workshops.Language', default=workshops.models.get_english, blank=True, verbose_name='What human language do you want the workshop to be run in?'),
        ),
        migrations.RunPython(migrate_language),
        migrations.RemoveField(
            model_name='eventrequest',
            name='language',
        ),
        migrations.RenameField(
            model_name='eventrequest',
            old_name='language_new',
            new_name='language',
        ),
    ]
