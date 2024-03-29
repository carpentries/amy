# Generated by Django 3.2.20 on 2023-07-31 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workshops', '0261_migrate_lesson_contribution_to_get_involved'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trainingrequest',
            name='training_completion_agreement',
            field=models.BooleanField(default=False, verbose_name='I agree to complete this training within three months of the training course. The completion steps are described at <a href="http://carpentries.github.io/instructor-training/checkout">http://carpentries.github.io/instructor-training/checkout</a>.'),
        ),
    ]
