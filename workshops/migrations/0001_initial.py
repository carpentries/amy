# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Airport',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('iata', models.CharField(unique=True, max_length=10)),
                ('fullname', models.CharField(unique=True, max_length=100)),
                ('country', models.CharField(max_length=100)),
                ('latitude', models.FloatField()),
                ('longitude', models.FloatField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Award',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('awarded', models.DateField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=40)),
                ('title', models.CharField(max_length=40)),
                ('criteria', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('published', models.BooleanField(default=False)),
                ('start', models.DateField(null=True, blank=True)),
                ('end', models.DateField(null=True, blank=True)),
                ('slug', models.CharField(null=True, max_length=100, blank=True)),
                ('url', models.CharField(max_length=100, null=True, unique=True, blank=True)),
                ('reg_key', models.CharField(null=True, max_length=20, blank=True)),
                ('attendance', models.IntegerField(null=True, blank=True)),
                ('admin_fee', models.DecimalField(null=True, max_digits=6, blank=True, decimal_places=2)),
                ('fee_paid', models.NullBooleanField(default=False)),
                ('notes', models.TextField(default='', blank=True)),
            ],
            options={
                'ordering': ('-start',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('personal', models.CharField(max_length=100)),
                ('middle', models.CharField(null=True, max_length=100, blank=True)),
                ('family', models.CharField(max_length=100)),
                ('email', models.CharField(max_length=100, null=True, unique=True, blank=True)),
                ('gender', models.CharField(null=True, max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True)),
                ('may_contact', models.BooleanField(default=True)),
                ('github', models.CharField(max_length=40, null=True, unique=True, blank=True)),
                ('twitter', models.CharField(max_length=40, null=True, unique=True, blank=True)),
                ('url', models.CharField(null=True, max_length=100, blank=True)),
                ('slug', models.CharField(null=True, max_length=100, blank=True)),
                ('airport', models.ForeignKey(to='workshops.Airport', null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Qualification',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('person', models.ForeignKey(to='workshops.Person')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=40)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('domain', models.CharField(unique=True, max_length=100)),
                ('fullname', models.CharField(unique=True, max_length=100)),
                ('country', models.CharField(null=True, max_length=100)),
                ('notes', models.TextField(default='')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(max_length=40)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('name', models.CharField(unique=True, max_length=40)),
                ('details', models.CharField(max_length=100)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('event', models.ForeignKey(to='workshops.Event')),
                ('person', models.ForeignKey(to='workshops.Person')),
                ('role', models.ForeignKey(to='workshops.Role')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='qualification',
            name='skill',
            field=models.ForeignKey(to='workshops.Skill'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='organizer',
            field=models.ForeignKey(related_name='organizer', to='workshops.Site', null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='site',
            field=models.ForeignKey(to='workshops.Site'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='event',
            name='tags',
            field=models.ManyToManyField(to='workshops.Tag'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='award',
            name='badge',
            field=models.ForeignKey(to='workshops.Badge'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='award',
            name='event',
            field=models.ForeignKey(to='workshops.Event', null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='award',
            name='person',
            field=models.ForeignKey(to='workshops.Person'),
            preserve_default=True,
        ),
    ]
