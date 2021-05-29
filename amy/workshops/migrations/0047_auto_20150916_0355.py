# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def add_empty_knowledge_domain(apps, schema_app):
    "A 'Don't know yet' KnowledgeDomain is required for EventRequest forms."
    KnowledgeDomain = apps.get_model('workshops', 'KnowledgeDomain')
    KnowledgeDomain.objects.get_or_create(name='Don\'t know yet')


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0046_eventrequest_language'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventrequest',
            name='attendee_domains',
            field=models.ManyToManyField(to='workshops.KnowledgeDomain', help_text="The attendees' academic field(s) of study, if known.", verbose_name='Domains or topic of interest for target audience'),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='language',
            field=models.CharField(default='English', blank=True, max_length=100, verbose_name='What human language do you want the workshop to be run in?'),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='location',
            field=models.CharField(max_length=100, help_text='City, Province, or State'),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='preferred_date',
            field=models.CharField(max_length=255, help_text='Please indicate when you would like to run the workshop. A range of at least a month is most helpful, although if you have specific dates you need the workshop, we will try to accommodate those requests.', verbose_name='Preferred workshop dates'),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='travel_reimbursement',
            field=models.CharField(default=None, blank=True, null=True, choices=[('', "Don't know yet."), ('book', 'Book travel through our university or program.'), ('reimburse', 'Book their own travel and be reimbursed.'), ('', 'Other (type below)')], max_length=40, verbose_name="How will instructors' travel and accommodations be managed?"),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='travel_reimbursement_other',
            field=models.CharField(blank=True, max_length=100, verbose_name="Other propositions for managing instructors' travel and accommodations"),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='understand_admin_fee',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(add_empty_knowledge_domain),
    ]
