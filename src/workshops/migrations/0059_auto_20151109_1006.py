from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps
from django.db.models import Q


def make_people_with_usable_passwords_active(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Password is unusable if:
    * it's empty, or
    * it starts with "!", or
    * it's using unknown hasher algorithm.

    We can iteratively test all people for all possible passwords, but the
    easiest way is forget about checking the hasher - since I know AMY has
    never changed it.
    """
    no_password = Q(password__isnull=True)
    empty_password = Q(password__exact="")
    unusable_password = Q(password__startswith="!")
    Person = apps.get_model("workshops", "Person")
    Person.objects.exclude(no_password | empty_password | unusable_password).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0058_auto_20151105_1452"),
    ]

    operations = [
        migrations.RunPython(make_people_with_usable_passwords_active),
    ]
