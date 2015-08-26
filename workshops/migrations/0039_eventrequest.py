# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0038_auto_20150809_0534'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventRequest',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False, verbose_name='ID', auto_created=True)),
                ('active', models.BooleanField(default=True)),
                ('name', models.CharField(max_length=40)),
                ('email', models.EmailField(max_length=254)),
                ('affiliation', models.CharField(help_text='University or Company', max_length=100)),
                ('location', models.CharField(help_text='City, Province or State, Country', max_length=100)),
                ('preferred_date', models.CharField(help_text='Please indicate when you would like to run the workshop. A range of a few weeks is most helpful, although we will try and accommodate requests to run workshops alongside conferences, etc.', max_length=100, verbose_name='Preferred workshop date')),
                ('approx_attendees', models.CharField(choices=[('20-40', '20-40 (one room, two instructors)'), ('40-80', '40-80 (two rooms, four instructors)'), ('80-120', '80-120 (three rooms, six instructors)')], help_text="This number doesn't need to be precise, but will help us decide how many instructors your workshop will need.", default='20-40', max_length=10, verbose_name='Approximate number of Attendees')),
                ('cover_travel_accomodation', models.BooleanField(default=False, verbose_name="My institution will cover instructors' travel and accommodation costs.")),
                ('understand_admin_fee', models.BooleanField(default=False, verbose_name="I understand the Software Carpentry Foundation's administrative fee.")),
                ('admin_fee_payment', models.CharField(choices=[('NP1', 'Non-profit: full fee for first workshop/year (US$1250)'), ('NP2', 'Non-profit: reduced fee for subsequent workshop/year (US$750)'), ('FP1', 'For-profit: full fee for first workshop/year (US$5000)'), ('FP2', 'For profit: reduced fee for subsequent workshop/year (US$3000)'), ('partner', 'No fee (my organization is a Partner or Affiliate)'), ('self-organized', 'No fee (self-organized workshop)'), ('waiver', 'Waiver requested (please give details in "Anything else")')], default='NP1', max_length=10, verbose_name='Which of the following applies to your payment for the administrative fee?')),
                ('comment', models.TextField(help_text='What else do you want us to know about your workshop? About your attendees? About you?', blank=True, verbose_name='Anything else?')),
                ('attendee_domains', models.ManyToManyField(help_text="The attendees' academic field(s) of study, if known.", to='workshops.KnowledgeDomain', blank=True, verbose_name='Attendee Field(s)')),
            ],
        ),
    ]
