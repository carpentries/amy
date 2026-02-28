import re

import django.core.validators
from django.db import migrations, models
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def switch_invoice_ni_to_na(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    """Switch 'not invoiced' to 'not applicable' in events' invoice status."""
    Event = apps.get_model("workshops", "Event")
    Event.objects.filter(invoice_status="ni-historic").update(invoice_status="na-historic")
    Event.objects.filter(invoice_status="ni-member").update(invoice_status="na-member")


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0072_underscore_usernames_fixed_migration"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="invoice_status",
            field=models.CharField(
                choices=[
                    ("unknown", "Unknown"),
                    ("invoiced", "Invoiced"),
                    ("not-invoiced", "Not invoiced"),
                    ("na-historic", "Not applicable for historical reasons"),
                    ("na-member", "Not applicable because of membership"),
                    ("na-self-org", "Not applicable because self-organized"),
                    ("na-waiver", "Not applicable because waiver granted"),
                    ("na-other", "Not applicable because other arrangements made"),
                ],
                blank=True,
                max_length=40,
                verbose_name="Invoice status",
                default="unknown",
            ),
        ),
        migrations.AlterField(
            model_name="person",
            name="username",
            field=models.CharField(
                validators=[django.core.validators.RegexValidator("^[\\w\\-_]+$", flags=re.A)],
                unique=True,
                max_length=40,
            ),
        ),
        migrations.RunPython(switch_invoice_ni_to_na),
    ]
