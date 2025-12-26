import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0010_merge"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="organizer",
            field=models.ForeignKey(
                null=True,
                to="workshops.Site",
                blank=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="organizer",
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="site",
            field=models.ForeignKey(to="workshops.Site", on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AlterField(
            model_name="person",
            name="airport",
            field=models.ForeignKey(
                null=True, to="workshops.Airport", blank=True, on_delete=django.db.models.deletion.PROTECT
            ),
        ),
    ]
