# Generated by Django 4.2.13 on 2024-05-17 21:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("emails", "0005_auto_20231217_1702"),
    ]

    operations = [
        migrations.AlterField(
            model_name="emailtemplate",
            name="body",
            field=models.TextField(
                help_text="Enter Markdown for email body. If you need to use loops, conditions, etc., use <a href='https://jinja.palletsprojects.com/en/3.1.x/templates/'>Jinja2 templates language</a>.",
                verbose_name="Email body (markdown)",
            ),
        ),
        migrations.AlterField(
            model_name="emailtemplate",
            name="subject",
            field=models.CharField(
                help_text="Enter text for email subject. If you need to use loops, conditions, etc., use <a href='https://jinja.palletsprojects.com/en/3.1.x/templates/'>Jinja2 templates language</a>.",
                max_length=255,
                verbose_name="Email subject",
            ),
        ),
    ]
