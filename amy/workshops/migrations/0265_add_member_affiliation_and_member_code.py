# Generated by Django 3.2.20 on 2023-09-18 11:23

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('workshops', '0264_trainingprogress_unique_trainee_at_event'),
    ]

    operations = [
        migrations.AddField(
            model_name='workshoprequest',
            name='member_affiliation',
            field=models.CharField(blank=True, choices=[('yes', 'Yes'), ('no', 'No'), ('unsure', "I'm not sure")], default='no', help_text='This may be the same as your institution above, or another institution.', max_length=40, verbose_name='Are you affiliated with a Carpentries member organization?'),
        ),
        migrations.AddField(
            model_name='workshoprequest',
            name='member_code',
            field=models.CharField(blank=True, default='', help_text='If you are affiliated with a Carpentries member organization, please enter the registration code associated with the membership. Your Member Affiliate can provide this.', max_length=40, verbose_name='Membership registration code'),
        ),
    ]
