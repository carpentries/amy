# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0038_auto_20150809_0534'),
    ]

    operations = [
        migrations.CreateModel(
            name='AcademicLevel',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('name', models.CharField(max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='ComputingExperienceLevel',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='EventRequest',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, verbose_name='ID', auto_created=True)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('name', models.CharField(max_length=40)),
                ('email', models.EmailField(max_length=254)),
                ('affiliation', models.CharField(help_text='University or Company', max_length=100)),
                ('location', models.CharField(help_text='City, Province or State, Country', max_length=100)),
                ('preferred_date', models.CharField(help_text='Please indicate when you would like to run the workshop. A range of a few weeks is most helpful, although we will try and accommodate requests to run workshops alongside conferences, etc.', max_length=100, verbose_name='Preferred workshop date')),
                ('approx_attendees', models.CharField(help_text="This number doesn't need to be precise, but will help us decide how many instructors your workshop will need.", default='20-40', choices=[('20-40', '20-40 (one room, two instructors)'), ('40-80', '40-80 (two rooms, four instructors)'), ('80-120', '80-120 (three rooms, six instructors)')], verbose_name='Approximate number of Attendees', max_length=40)),
                ('attendee_domains_other', models.CharField(max_length=100, help_text='If none of the fields above works for you.', verbose_name='Other field', default='', blank=True)),
                ('cover_travel_accomodation', models.BooleanField(default=False, verbose_name="My institution will cover instructors' travel and accommodation costs.")),
                ('understand_admin_fee', models.BooleanField(default=False, verbose_name="I understand the Software Carpentry Foundation's administrative fee.")),
                ('admin_fee_payment', models.CharField(max_length=40, default='NP1', verbose_name='Which of the following applies to your payment for the administrative fee?', choices=[('NP1', 'Non-profit: full fee for first workshop/year (US$1250)'), ('NP2', 'Non-profit: reduced fee for subsequent workshop/year (US$750)'), ('FP1', 'For-profit: full fee for first workshop/year (US$5000)'), ('FP2', 'For profit: reduced fee for subsequent workshop/year (US$3000)'), ('partner', 'No fee (my organization is a Partner or Affiliate)'), ('self-organized', 'No fee (self-organized workshop)'), ('waiver', 'Waiver requested (please give details in "Anything else")')])),
                ('comment', models.TextField(help_text='What else do you want us to know about your workshop? About your attendees? About you?', blank=True, verbose_name='Anything else?')),
                ('attendee_academic_levels', models.ManyToManyField(help_text='If you know the academic level(s) of your attendees, indicate them here.', to='workshops.AcademicLevel', verbose_name="Attendees' Academic Level")),
                ('attendee_computing_levels', models.ManyToManyField(help_text="Indicate the attendees' level of computing experience, if known. We will ask attendees to fill in a skills survey before the workshop, so this answer can be an approximation.", to='workshops.ComputingExperienceLevel', verbose_name="Attendees' level of computing experience")),
                ('attendee_domains', models.ManyToManyField(help_text="The attendees' academic field(s) of study, if known.", blank=True, to='workshops.KnowledgeDomain', verbose_name='Attendee Field(s)')),
            ],
        ),
    ]
