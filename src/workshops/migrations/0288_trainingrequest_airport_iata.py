from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0287_alter_person_badges"),
    ]

    operations = [
        migrations.AddField(
            model_name="trainingrequest",
            name="airport_iata",
            field=models.CharField(
                blank=True,
                default="",
                help_text="Nearest major airport (IATA code: https://www.world-airport-codes.com/)",
                max_length=10,
            ),
        ),
    ]
