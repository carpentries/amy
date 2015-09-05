# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.db import models, migrations

from workshops.models import (
    Airport, Award, Badge, Event, Host, KnowledgeDomain, Lesson, Person,
    Qualification, Role, Tag, Task,
)


def add_permission_groups(apps, schema_editor):
    # create 'administrators' group with all permissions for CRUD
    auth_ct = ContentType.objects.get_for_models(Permission, Group)
    workshops_ct = ContentType.objects.get_for_models(
        Airport, Award, Badge, Event, Host, KnowledgeDomain, Lesson, Person,
        Qualification, Role, Tag, Task,
    )
    auth_ct.update(workshops_ct)
    permissions = Permission.objects.filter(content_type__in=auth_ct.values())

    group = Group.objects.create(name='administrators')
    group.permissions = permissions
    group.save()

    # create 'steering committee' group, but don't grant any permissions (cause
    # read-only access doesn't require any)
    Group.objects.create(name='steering committee')


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0038_auto_20150809_0534'),
    ]

    operations = [
        migrations.RunPython(add_permission_groups),
    ]
