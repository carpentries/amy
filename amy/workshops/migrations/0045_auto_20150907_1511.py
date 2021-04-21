# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0044_add_dataanalysislevels'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventrequest',
            name='admin_fee_payment',
            field=models.CharField(verbose_name='Which of the following applies to your payment for the administrative fee?', default='NP1', max_length=40, choices=[('NP1', 'Non-profit / non-partner: US$2500'), ('partner', 'Partner: US$1250'), ('FP1', 'For-profit: US$10,000'), ('self-organized', 'Self-organized: no fee (please let us know if you wish to make a donation)'), ('waiver', 'Waiver requested (please give details in "Anything else")')]),
        ),
        migrations.AlterField(
            model_name='eventrequest',
            name='approx_attendees',
            field=models.CharField(verbose_name='Approximate number of Attendees', default='20-40', max_length=40, choices=[('1-20', '1-20 (one room, one instructor)'), ('20-40', '20-40 (one room, two instructors)'), ('40-80', '40-80 (two rooms, four instructors)'), ('80-120', '80-120 (three rooms, six instructors)')], help_text="This number doesn't need to be precise, but will help us decide how many instructors your workshop will need."),
        ),
    ]
