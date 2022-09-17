# Generated by Django 3.2.14 on 2022-08-14 20:45

from django.db import migrations, models


def update_link_for_existing_curriculums(apps, schema_editor) -> None:
    Curriculum = apps.get_model("workshops", "Curriculum")

    DATA = {
        "dc-ecology-python": "https://datacarpentry.org/lessons/#ecology-workshop",
        "dc-ecology-r": "https://datacarpentry.org/lessons/#ecology-workshop",
        "dc-genomics": "https://datacarpentry.org/lessons/#genomics-workshop",
        "dc-geospatial": "https://datacarpentry.org/lessons/#geospatial-curriculum",
        "dc-other": "https://datacarpentry.org/lessons/",
        "dc-socsci-python": "https://datacarpentry.org/lessons/#social-science-curriculum",
        "dc-socsci-r": "https://datacarpentry.org/lessons/#social-science-curriculum",
        "lc": "https://librarycarpentry.org/lessons/",
        "lc-other": "https://librarycarpentry.org/lessons/",
        "swc-es-python": "https://software-carpentry.org/lessons/",
        "swc-es-r": "https://software-carpentry.org/lessons/",
        "swc-es-other": "https://software-carpentry.org/lessons/",
        "swc-plotting": "https://software-carpentry.org/lessons/",
        "swc-python": "https://software-carpentry.org/lessons/",
        "swc-r": "https://software-carpentry.org/lessons/",
        "swc-reproducible-science": "https://software-carpentry.org/lessons/",
    }

    affected_rows = 0
    for name, website in DATA.items():
        affected_rows += Curriculum.objects.filter(slug=name).update(website=website)

    print(f"Affected rows by the migration: {affected_rows}")


class Migration(migrations.Migration):

    dependencies = [
        ("workshops", "0252_auto_20211231_1108"),
    ]

    operations = [
        migrations.AddField(
            model_name="curriculum",
            name="website",
            field=models.URLField(
                blank=True, default="", verbose_name="Curriculum page"
            ),
        ),
        migrations.RunPython(
            update_link_for_existing_curriculums, migrations.RunPython.noop
        ),
    ]