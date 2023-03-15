# Written by @elichad 2023-03-15

from django.db import migrations, models

term_descriptions = {
    "may-contact": "May contact",
    "public-profile": "Consent to making profile public",
    "may-publish-name": "Consent to include name when publishing lessons",
    "privacy-policy": "Privacy policy agreement",
}


def set_term_descriptions(apps, schema_editor):
    Term = apps.get_model("consents", "Term")
    for term in Term.objects.all():
        term.short_description = term_descriptions.get(
            term.slug, term.slug.replace("-", " ").capitalize()
        )
        term.save(update_fields=["short_description"])


class Migration(migrations.Migration):

    dependencies = [
        ("consents", "0006_auto_20210614_1234"),
    ]

    operations = [
        # add field and make it temporarily nullable
        migrations.AddField(
            model_name="term",
            name="short_description",
            field=models.CharField(null=True, max_length=100),
        ),
        # set descriptions for existing terms
        migrations.RunPython(
            set_term_descriptions, reverse_code=migrations.RunPython.noop
        ),
        # make field non-nullable
        migrations.AlterField(
            model_name="term",
            name="short_description",
            field=models.CharField(max_length=100),
        ),
    ]
