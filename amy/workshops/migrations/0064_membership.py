# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0063_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, verbose_name='ID', primary_key=True)),
                ('variant', models.CharField(choices=[('partner', 'Partner'), ('affiliate', 'Affiliate'), ('sponsor', 'Sponsor')], max_length=40)),
                ('agreement_start', models.DateField(blank=True, default=django.utils.timezone.now, null=True)),
                ('agreement_end', models.DateField(blank=True, default=django.utils.timezone.now, null=True)),
                ('contribution_type', models.CharField(blank=True, choices=[('financial', 'Financial'), ('person-days', 'Person-days'), ('other', 'Other')], max_length=40, null=True)),
                ('workshops_without_admin_fee_per_year', models.PositiveIntegerField(help_text='Acceptable number of workshops without admin fee per year', blank=True, null=True)),
                ('self_organized_workshops_per_year', models.PositiveIntegerField(help_text='Imposed number of self-organized workshops per year', blank=True, null=True)),
                ('notes', models.TextField(blank=True, default='')),
            ],
        ),
        migrations.AddField(
            model_name='host',
            name='membership',
            field=models.OneToOneField(to='workshops.Membership', null=True, on_delete=django.db.models.deletion.SET_NULL),
        ),
    ]
