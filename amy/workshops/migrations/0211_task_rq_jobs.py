# Generated by Django 2.2.5 on 2019-10-29 19:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0210_auto_20200124_1939'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='rq_jobs',
            field=models.ManyToManyField(blank=True, help_text='This should be filled out by AMY itself.', to='autoemails.RQJob', verbose_name='Related Redis Queue jobs'),
        ),
    ]
