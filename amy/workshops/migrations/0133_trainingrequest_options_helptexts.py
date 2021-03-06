# -*- coding: utf-8 -*-
# Generated by Django 1.9.12 on 2018-03-04 20:57
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0132_trainingrequest_reword_location_help'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profileupdaterequest',
            name='occupation',
            field=models.CharField(blank=True, choices=[('undisclosed', 'Prefer not to say'), ('undergrad', 'Undergraduate student'), ('grad', 'Graduate student'), ('postdoc', 'Post-doctoral researcher'), ('faculty', 'Faculty'), ('research', 'Research staff (including research programmer)'), ('support', 'Support staff (including technical support)'), ('librarian', 'Librarian/archivist'), ('commerce', 'Commercial software developer '), ('', 'Other:')], default='undisclosed', help_text='Please choose the one that best describes you.', max_length=40, verbose_name='What is your current occupation/career stage?'),
        ),
        migrations.AlterField(
            model_name='trainingrequest',
            name='group_name',
            field=models.CharField(blank=True, default='', help_text='If you are scheduled to receive training at a member site, please enter the group name you were provided.', max_length=100, verbose_name='Group name'),
        ),
        migrations.AlterField(
            model_name='trainingrequest',
            name='max_travelling_frequency',
            field=models.CharField(choices=[('not-at-all', 'Not at all'), ('yearly', 'Once a year'), ('often', 'Several times a year'), ('other', 'Other:')], default='not-at-all', help_text=None, max_length=40, verbose_name='How frequently would you be able to travel to teach such classes?'),
        ),
        migrations.AlterField(
            model_name='trainingrequest',
            name='occupation',
            field=models.CharField(blank=True, choices=[('undisclosed', 'Prefer not to say'), ('undergrad', 'Undergraduate student'), ('grad', 'Graduate student'), ('postdoc', 'Post-doctoral researcher'), ('faculty', 'Faculty'), ('research', 'Research staff (including research programmer)'), ('support', 'Support staff (including technical support)'), ('librarian', 'Librarian/archivist'), ('commerce', 'Commercial software developer '), ('', 'Other:')], default='undisclosed', help_text='Please choose the one that best describes you.', max_length=40, verbose_name='What is your current occupation/career stage?'),
        ),
        migrations.AlterField(
            model_name='trainingrequest',
            name='previous_experience',
            field=models.CharField(choices=[('none', 'None'), ('hours', 'A few hours'), ('workshop', 'A workshop (full day or longer)'), ('ta', 'Teaching assistant for a full course'), ('courses', 'Primary instructor for a full course'), ('other', 'Other:')], default='none', help_text='Please include teaching experience at any level from grade school to post-secondary education.', max_length=40, verbose_name='Previous experience in teaching'),
        ),
        migrations.AlterField(
            model_name='trainingrequest',
            name='previous_training',
            field=models.CharField(choices=[('none', 'None'), ('hours', 'A few hours'), ('workshop', 'A workshop'), ('course', 'A certification or short course'), ('full', 'A full degree'), ('other', 'Other:')], default='none', help_text=None, max_length=40, verbose_name='Previous formal training as a teacher or instructor'),
        ),
        migrations.AlterField(
            model_name='trainingrequest',
            name='teaching_frequency_expectation',
            field=models.CharField(choices=[('not-at-all', 'Not at all'), ('yearly', 'Once a year'), ('monthly', 'Several times a year'), ('other', 'Other:')], default='not-at-all', help_text=None, max_length=40, verbose_name='How often would you expect to teach Carpentry Workshops after this training?'),
        ),
        migrations.AlterField(
            model_name='trainingrequest',
            name='training_completion_agreement',
            field=models.BooleanField(default=False, verbose_name='I agree to complete this training within three months of the training course. The completion steps are described at <a href="http://carpentries.github.io/instructor-training/checkout/">http://carpentries.github.io/instructor-training/checkout/</a>.'),
        ),
    ]
