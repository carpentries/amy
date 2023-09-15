# Generated by Django 3.2.20 on 2023-09-15 16:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0264_auto_20230912_1319'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workshoprequest',
            name='membership_affiliation',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unsure', "I'm not sure")], default=False, help_text='This may be the same as your institution above, or another institution.', max_length=40, verbose_name='Are you affiliated with a Carpentries member organization?'),
        ),
        migrations.AlterField(
            model_name='workshoprequest',
            name='membership_code',
            field=models.CharField(blank=True, default='', help_text='If you are affiliated with a Carpentries member organization, please enter the registration code associated with the membership.', max_length=40, verbose_name='Membership registration code'),
        ),
    ]
