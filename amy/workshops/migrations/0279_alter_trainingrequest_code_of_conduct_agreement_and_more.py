# Generated by Django 4.2.20 on 2025-06-09 20:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0278_alter_membership_rolled_to_membership'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainingrequest',
            name='code_of_conduct_agreement',
            field=models.BooleanField(default=False, verbose_name='I agree to abide by The Carpentries\' <a href="https://docs.carpentries.org/policies/coc/" target="_blank" rel="noreferrer">Code of Conduct</a>.'),
        ),
        migrations.AlterField(
            model_name='trainingrequest',
            name='data_privacy_agreement',
            field=models.BooleanField(default=False, verbose_name='I have read and agree to <a href="https://docs.carpentries.org/policies/privacy.html" target="_blank" rel="noreferrer">the data privacy policy</a> of The Carpentries.'),
        ),
        migrations.AlterField(
            model_name='workshoprequest',
            name='code_of_conduct_agreement',
            field=models.BooleanField(default=False, verbose_name='I agree to abide by The Carpentries\' <a href="https://docs.carpentries.org/policies/coc/" target="_blank" rel="noreferrer">Code of Conduct</a>.'),
        ),
        migrations.AlterField(
            model_name='workshoprequest',
            name='data_privacy_agreement',
            field=models.BooleanField(default=False, verbose_name='I have read and agree to <a href="https://docs.carpentries.org/policies/privacy.html" target="_blank" rel="noreferrer">the data privacy policy</a> of The Carpentries.'),
        ),
        migrations.AlterField(
            model_name='workshoprequest',
            name='host_responsibilities',
            field=models.BooleanField(default=False, verbose_name="I understand <a href='https://docs.carpentries.org/resources/workshops/checklists.html'>the responsibilities of the workshop host</a>, including recruiting local helpers to support the workshop (1 helper for every 8-10 learners)."),
        ),
    ]
