# Generated by Django 2.2.26 on 2022-02-20 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recruitment', '0002_instructorrecruitment_assigned_to'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instructorrecruitmentsignup',
            name='interest',
            field=models.CharField(choices=[('session', 'Whole session'), ('part', 'Part of session'), ('support', 'Supporting instructor')], default='session', max_length=10),
        ),
    ]
