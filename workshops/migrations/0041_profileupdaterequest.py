# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0040_auto_20150827_1715'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfileUpdateRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('personal', models.CharField(max_length=100, verbose_name='Personal (first) name')),
                ('family', models.CharField(max_length=100, verbose_name='Family (last) name')),
                ('email', models.CharField(max_length=100, verbose_name='Email address')),
                ('affiliation', models.CharField(max_length=100, help_text='What university, company, lab, or other organization are you affiliated with (if any)?')),
                ('airport_iata', models.CharField(max_length=3, help_text='Please use its 3-letter IATA code (<a href="http://www.airportcodes.aero/">http://www.airportcodes.aero/</a>) to tell us where you\'re located.', verbose_name='Nearest major airport')),
                ('occupation', models.CharField(max_length=40, blank=True, null=True, choices=[(None, 'Prefer not to say'), ('undergrad', 'Undergraduate student'), ('grad', 'Graduate student'), ('postdoc', 'Post-doctoral researcher'), ('faculty', 'Faculty'), ('research', 'Research staff (including research programmer)'), ('support', 'Support staff (including technical support)'), ('librarian', 'Librarian/archivist'), ('commerce', 'Commercial software developer '), ('', 'Other (enter below)')], verbose_name='What is your current occupation/career stage?', help_text='Please choose the one that best describes you.')),
                ('occupation_other', models.CharField(default='', max_length=100, blank=True, verbose_name='Other occupation/career stage')),
                ('github', models.CharField(default='', max_length=100, blank=True, verbose_name='GitHub username', help_text='Please provide your username, not a numeric user ID.')),
                ('twitter', models.CharField(default='', max_length=100, blank=True, verbose_name='Twitter username', help_text='Please, do not put "@" at the beginning.')),
                ('orcid', models.CharField(default='', max_length=100, blank=True, verbose_name='ORCID ID')),
                ('website', models.CharField(default='', max_length=100, blank=True, verbose_name='Personal website')),
                ('gender', models.CharField(max_length=1, blank=True, null=True, choices=[(None, 'Prefer not to say'), ('F', 'Female'), ('M', 'Male'), ('O', 'Other (enter below)')])),
                ('gender_other', models.CharField(default='', max_length=100, blank=True, verbose_name='Other gender')),
                ('domains_other', models.CharField(default='', max_length=255, blank=True, verbose_name='Other areas of expertise')),
                ('lessons_other', models.CharField(default='', max_length=255, blank=True, verbose_name="Other topics/lessons you're comfortable teaching", help_text='Please include lesson URLs.')),
                ('domains', models.ManyToManyField(to='workshops.KnowledgeDomain', blank=True, verbose_name='Areas of expertise', help_text='Please check all that apply.')),
                ('lessons', models.ManyToManyField(to='workshops.Lesson', blank=True, verbose_name="Topic and lessons you're comfortable teaching", help_text='Please mark ALL that apply.')),
            ],
        ),
    ]
