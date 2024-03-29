# Generated by Django 3.2.16 on 2023-02-07 18:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0254_alter_trainingrequest_github'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainingrequest',
            name='family',
            field=models.CharField(blank=True, max_length=100, verbose_name='Family name (surname)'),
        ),
        migrations.AlterField(
            model_name='trainingrequest',
            name='underrepresented_details',
            field=models.CharField(blank=True, default='', help_text="This response is optional and doesn't impact your application's ranking.", max_length=255, verbose_name='If you are comfortable doing so, please share more details.'),
        ),
    ]
