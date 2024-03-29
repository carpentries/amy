# Generated by Django 3.2.20 on 2023-11-16 09:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0265_auto_20231108_1357"),
    ]

    operations = [
        migrations.AddField(
            model_name="workshoprequest",
            name="member_code",
            field=models.CharField(
                blank=True,
                default="",
                help_text="If you are affiliated with a Carpentries member organization, please enter the registration code associated with the membership. Your Member Affiliate can provide this.",
                max_length=40,
                verbose_name="Membership registration code",
            ),
        ),
        migrations.RenameField(
            model_name="trainingrequest",
            old_name="group_name",
            new_name="member_code",
        ),
        migrations.AddField(
            model_name="trainingrequest",
            name="member_code_override",
            field=models.BooleanField(
                blank=True,
                default=False,
                help_text="A member of our team will check the code and follow up with you if there are any problems that require your attention.",
                verbose_name="Continue with registration code marked as invalid",
            ),
        ),
    ]
