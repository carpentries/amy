from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps


def add_data_analysis_levels(apps: StateApps, schema_editor: BaseDatabaseSchemaEditor) -> None:
    DataAnalysisLevel = apps.get_model("workshops", "DataAnalysisLevel")
    L = [
        "Little to no prior computational experience",
        "Some experience with data analysis in programming languages like R, SAS, Matlab or Python",
        "Experienced in data analysis, but need to know how to work with "
        "different data types or bigger data or computer cluster",
    ]
    for name in L:
        DataAnalysisLevel.objects.create(name=name)


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0043_auto_20150903_1508"),
    ]

    operations = [
        migrations.RunPython(add_data_analysis_levels),
    ]
