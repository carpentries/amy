# Generated by Django 3.2.19 on 2023-07-12 21:11

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0002_auto_20230703_2116'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emailtemplate',
            name='bcc_header',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.EmailField(max_length=254), blank=True, size=None, verbose_name='BCC (header)'),
        ),
        migrations.AlterField(
            model_name='emailtemplate',
            name='cc_header',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.EmailField(max_length=254), blank=True, size=None, verbose_name='CC (header)'),
        ),
    ]
