# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(verbose_name='last login', default=django.utils.timezone.now)),
                ('is_superuser', models.BooleanField(verbose_name='superuser status', default=False, help_text='Designates that this user has all permissions without explicitly assigning them.')),
                ('personal', models.CharField(max_length=100)),
                ('middle', models.CharField(max_length=100, blank=True, null=True)),
                ('family', models.CharField(max_length=100)),
                ('email', models.CharField(unique=True, max_length=100, blank=True, null=True)),
                ('gender', models.CharField(max_length=1, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')], blank=True, null=True)),
                ('may_contact', models.BooleanField(default=True)),
                ('github', models.CharField(unique=True, max_length=40, blank=True, null=True)),
                ('twitter', models.CharField(unique=True, max_length=40, blank=True, null=True)),
                ('url', models.CharField(max_length=100, blank=True, null=True)),
                ('slug', models.CharField(max_length=100, blank=True, null=True)),
                ('username', models.CharField(unique=True, max_length=40)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Airport',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
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
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('awarded', models.DateField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Badge',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
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
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('published', models.BooleanField(default=False)),
                ('start', models.DateField(blank=True, null=True)),
                ('end', models.DateField(blank=True, null=True)),
                ('slug', models.CharField(max_length=100, blank=True, null=True)),
                ('url', models.CharField(unique=True, max_length=100, blank=True, null=True)),
                ('reg_key', models.CharField(max_length=20, blank=True, null=True)),
                ('attendance', models.IntegerField(blank=True, null=True)),
                ('admin_fee', models.DecimalField(decimal_places=2, max_digits=6, blank=True, null=True)),
                ('fee_paid', models.NullBooleanField(default=False)),
                ('notes', models.TextField(default='', blank=True)),
            ],
            options={
                'ordering': ('-start',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Qualification',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('person', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=40)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('domain', models.CharField(unique=True, max_length=100)),
                ('fullname', models.CharField(unique=True, max_length=100)),
                ('country', models.CharField(max_length=100, null=True)),
                ('notes', models.TextField(default='')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=40)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
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
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('event', models.ForeignKey(to='workshops.Event')),
                ('person', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
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
            field=models.ForeignKey(blank=True, related_name='organizer', null=True, to='workshops.Site'),
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
            field=models.ForeignKey(blank=True, null=True, to='workshops.Event'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='award',
            name='person',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='person',
            name='airport',
            field=models.ForeignKey(blank=True, null=True, to='workshops.Airport'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='person',
            name='groups',
            field=models.ManyToManyField(related_name='user_set', verbose_name='groups', blank=True, related_query_name='user', help_text='The groups this user belongs to. A user will get all permissions granted to each of his/her group.', to='auth.Group'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='person',
            name='user_permissions',
            field=models.ManyToManyField(related_name='user_set', verbose_name='user permissions', blank=True, related_query_name='user', help_text='Specific permissions for this user.', to='auth.Permission'),
            preserve_default=True,
        ),
    ]
