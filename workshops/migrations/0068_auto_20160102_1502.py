# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


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
    ]
