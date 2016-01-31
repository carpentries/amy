# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import email.parser
import urllib.request

from django.db import migrations, models
from django.conf import settings


def add_languages(
        apps, schema_editor,
        url='http://www.iana.org/assignments/language-subtag-registry/language-subtag-registry'):
    """Populate the Languages table.

    [1] lists IANA as the registry maintainer, [2] looks like that
    registry, and [3] describes the entry-format in the registry.

    [1]: https://tools.ietf.org/html/rfc5646#section-2.2.1
    [2]: http://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
    [3]: https://tools.ietf.org/html/rfc5646#section-3.1
    """
    with urllib.request.urlopen(url=url) as response:
        payload_bytes = response.read()
        charset = response.headers.get_content_charset()
        payload = payload_bytes.decode(charset)
    Language = apps.get_model('workshops', 'Language')
    record = []
    for line in payload.splitlines():
        if line == '%%':
            add_language(record=record, Language=Language)
            record = []
        else:
            record.append(line)
    add_language(record=record, Language=Language)


def add_language(record, Language):
    if len(record) == 0:
        return
    # https://tools.ietf.org/html/rfc5646#section-3.1.2
    if len(record) == 1 and record[0].startswith('File-Date:'):
        return
    # https://docs.python.org/3/library/email.parser.html#parser-class-api
    # to handle line-wrapping
    # https://tools.ietf.org/html/rfc5646#section-3.1.1
    fields = email.parser.Parser().parsestr('\r\n'.join(record))
    if fields['Type'] != 'language':
        return
    if len(fields['Subtag']) > 2:
        # skip these until we need them
        # https://github.com/swcarpentry/amy/issues/582#issuecomment-159506884
        return
    Language.objects.get_or_create(
        name=fields['Description'],
        language=fields['Subtag'],
    )


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0067_person_username_regexvalidator'),
    ]

    operations = [
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('name', models.CharField(max_length=40, help_text='Description of this language tag in English')),
                ('language', models.CharField(max_length=10, help_text='Primary language subtag.  https://tools.ietf.org/html/rfc5646#section-2.2.1')),
            ],
        ),
        migrations.CreateModel(
            name='LanguageQualification',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('weight', models.FloatField(default=1, help_text='https://tools.ietf.org/html/rfc7231#section-5.3.1')),
                ('language', models.ForeignKey(to='workshops.Language')),
                ('person', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='person',
            name='languages',
            field=models.ManyToManyField(to='workshops.Language', through='workshops.LanguageQualification', blank=True),
        ),
        migrations.RunPython(add_languages),
    ]
