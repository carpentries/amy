# Generated by Django 2.2.24 on 2021-10-21 19:43

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('workshops', '0250_auto_20210807_1951'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CommunityRoleInactivation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('name', models.CharField(max_length=150)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CommunityRoleConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('name', models.CharField(max_length=150)),
                ('display_name', models.CharField(max_length=150)),
                ('link_to_award', models.BooleanField(verbose_name='Should link to an Award?')),
                ('link_to_membership', models.BooleanField(verbose_name='Should link to a Membership?')),
                ('additional_url', models.BooleanField(verbose_name='Should allow for additional URL?')),
                ('generic_relation_multiple_items', models.BooleanField(verbose_name='Should generic relation point to more than 1 items?')),
                ('award_badge_limit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='workshops.Badge')),
                ('generic_relation_content_type', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.ContentType')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='CommunityRole',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_updated_at', models.DateTimeField(auto_now=True, null=True)),
                ('start', models.DateField(blank=True, null=True)),
                ('end', models.DateField(blank=True, null=True)),
                ('url', models.URLField(blank=True, default='', verbose_name='URL')),
                ('generic_relation_m2m', django.contrib.postgres.fields.ArrayField(blank=True, base_field=models.PositiveIntegerField(), default=list, size=None)),
                ('award', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='workshops.Award')),
                ('config', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='communityroles.CommunityRoleConfig')),
                ('inactivation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='communityroles.CommunityRoleInactivation')),
                ('membership', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='workshops.Membership')),
                ('person', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
