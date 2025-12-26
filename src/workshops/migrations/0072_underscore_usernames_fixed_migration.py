from django.db import migrations


def change_dots_to_underscores(apps, schema_editor):
    """Replace '.' with '_' in every username."""
    Person = apps.get_model("workshops", "Person")
    persons = Person.objects.filter(username__contains=".")
    for person in persons:
        person.username = person.username.replace(".", "_")
        person.save()


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0071_merge"),
    ]

    operations = [
        migrations.RunPython(change_dots_to_underscores),
    ]
