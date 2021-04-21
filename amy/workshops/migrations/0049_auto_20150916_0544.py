# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0048_auto_20150916_0441'),
    ]

    operations = [
        migrations.AlterField(
            model_name='person',
            name='gender',
            field=models.CharField(max_length=1, default='U', choices=[('U', 'Prefer not to say (undisclosed)'), ('M', 'Male'), ('F', 'Female'), ('O', 'Other')]),
        ),
        migrations.AlterField(
            model_name='profileupdaterequest',
            name='airport_iata',
            field=models.CharField(help_text='Please use its 3-letter IATA code (<a href="http://www.airportcodes.aero/" target="_blank">http://www.airportcodes.aero/</a>) to tell us where you\'re located.', max_length=3, verbose_name='Nearest major airport'),
        ),
        migrations.AlterField(
            model_name='profileupdaterequest',
            name='email',
            field=models.EmailField(max_length=254, verbose_name='Email address'),
        ),
        migrations.AlterField(
            model_name='profileupdaterequest',
            name='gender',
            field=models.CharField(max_length=1, default='U', choices=[('U', 'Prefer not to say'), ('F', 'Female'), ('M', 'Male'), ('O', 'Other (enter below)')]),
        ),
        migrations.AlterField(
            model_name='profileupdaterequest',
            name='lessons',
            field=models.ManyToManyField(help_text='Please mark ALL that apply.', to='workshops.Lesson', verbose_name="Topic and lessons you're comfortable teaching"),
        ),
        migrations.AlterField(
            model_name='profileupdaterequest',
            name='occupation',
            field=models.CharField(blank=True, help_text='Please choose the one that best describes you.', choices=[('undisclosed', 'Prefer not to say'), ('undergrad', 'Undergraduate student'), ('grad', 'Graduate student'), ('postdoc', 'Post-doctoral researcher'), ('faculty', 'Faculty'), ('research', 'Research staff (including research programmer)'), ('support', 'Support staff (including technical support)'), ('librarian', 'Librarian/archivist'), ('commerce', 'Commercial software developer '), ('', 'Other (enter below)')], max_length=40, default='undisclosed', verbose_name='What is your current occupation/career stage?'),
        ),
        migrations.AlterField(
            model_name='profileupdaterequest',
            name='twitter',
            field=models.CharField(blank=True, max_length=100, default='', verbose_name='Twitter username'),
        ),
    ]
