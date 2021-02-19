# Generated by Django 2.2.17 on 2021-02-17 20:55

from django.db import migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0230_membership_persons'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='country',
            field=django_countries.fields.CountryField(blank=True, help_text='Required in order for this event to be "published".<br />For Data, Library, or Software Carpentry workshops, always use the country of the host organisation. <br />For Instructor Training, use the country only for in-person events, and use <b>Online</b> for online events. <br />Be sure to use the <b>online tag</b> above for all online events.', max_length=2, null=True),
        ),
    ]