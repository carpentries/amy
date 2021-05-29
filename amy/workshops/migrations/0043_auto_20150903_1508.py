# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0042_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='DataAnalysisLevel',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
            ],
        ),
        migrations.AddField(
            model_name='eventrequest',
            name='conference',
            field=models.CharField(verbose_name='If the workshop is to be associated with a conference or meeting, which one? ', default='', max_length=100, blank=True),
        ),
        migrations.AddField(
            model_name='eventrequest',
            name='country',
            field=django_countries.fields.CountryField(default='US', max_length=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='eventrequest',
            name='data_types',
            field=models.CharField(verbose_name='We currently have developed or are developing workshops focused on four types of data. Please let us know which workshop would best suit your needs.', blank=True, max_length=40, choices=[('survey', 'Survey data (ecology, biodiversity, social science)'), ('genomic', 'Genomic data'), ('geospatial', 'Geospatial data'), ('text-mining', 'Text mining'), ('', 'Other (type below)')]),
        ),
        migrations.AddField(
            model_name='eventrequest',
            name='data_types_other',
            field=models.CharField(verbose_name='Other data domains for the workshop', max_length=100, blank=True),
        ),
        migrations.AddField(
            model_name='eventrequest',
            name='fee_waiver_request',
            field=models.BooleanField(help_text="Waiver's of the administrative fee are available on a needs basis. If you are interested in submitting a waiver application please indicate here.", default=False, verbose_name='I would like to submit an administrative fee waiver application'),
        ),
        migrations.AddField(
            model_name='eventrequest',
            name='travel_reimbursement',
            field=models.CharField(choices=[('', "Don't know yet."), ('book', 'Book travel through our university or program.'), ('reimburse', 'Book their own travel and be reimbursed.'), ('', 'Other (type below)')], null=True, max_length=40, blank=True, verbose_name='For instructor travel, how will instructors be reimbursed?', default=None),
        ),
        migrations.AddField(
            model_name='eventrequest',
            name='travel_reimbursement_other',
            field=models.CharField(verbose_name='Other type of reimbursement', max_length=100, blank=True),
        ),
        migrations.AddField(
            model_name='eventrequest',
            name='workshop_type',
            field=models.CharField(default='swc', max_length=40, choices=[('swc', 'Software-Carpentry'), ('dc', 'Data-Carpentry')]),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='attendee_domains',
            field=models.ManyToManyField(help_text="The attendees' academic field(s) of study, if known.", to='workshops.KnowledgeDomain', blank=True, verbose_name='Domains or topic of interest for target audience'),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='attendee_domains_other',
            field=models.CharField(help_text='If none of the fields above works for you.', blank=True, default='', max_length=100, verbose_name='Other domains or topics of interest'),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='location',
            field=models.CharField(help_text='City, Province or State', max_length=100),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='preferred_date',
            field=models.CharField(help_text='Please indicate when you would like to run the workshop. A range of at least a month is most helpful, although if you have a specific date or dates you need the workshop, we will try to accommodate those requests.', max_length=255, verbose_name='Preferred workshop date'),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='understand_admin_fee',
            field=models.BooleanField(help_text='<a href="http://software-carpentry.org/blog/2015/07/changes-to-admin-fee.html">Look up administration fees</a>', default=False, verbose_name="I understand the Software Carpentry Foundation's administration fee."),
        ),
        migrations.AddField(
            model_name='eventrequest',
            name='attendee_data_analysis_level',
            field=models.ManyToManyField(help_text="If you know, indicate learner's general level of data analysis experience", to='workshops.DataAnalysisLevel', verbose_name='Level of data analysis experience'),
        ),
    ]
