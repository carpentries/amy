import django_countries.fields
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0010_merge"),
    ]

    operations = [
        migrations.AlterField(
            model_name="site",
            name="country",
            field=django_countries.fields.CountryField(blank=True, max_length=2, null=True),
        ),
    ]
