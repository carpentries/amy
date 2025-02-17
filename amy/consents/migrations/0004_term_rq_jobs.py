# Generated by Django 2.2.17 on 2021-04-15 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('consents', '0003_term_help_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='term',
            name='rq_jobs',
            field=models.ManyToManyField(blank=True, help_text='This should be filled out by AMY itself.', to='autoemails.RQJob', verbose_name='Related Redis Queue jobs'),
        ),
    ]
