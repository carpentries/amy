# Generated by Django 3.2.20 on 2023-11-08 13:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workshops", "0264_trainingprogress_unique_trainee_at_event"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="trainingrequest",
            name="training_completion_agreement",
        ),
        migrations.RemoveField(
            model_name="trainingrequest",
            name="workshop_teaching_agreement",
        ),
        migrations.AddField(
            model_name="trainingrequest",
            name="checkout_intent",
            field=models.CharField(
                choices=[("yes", "Yes"), ("no", "No"), ("unsure", "Not sure")],
                default="unsure",
                help_text='The checkout process is described on our <a href="https://carpentries.github.io/instructor-training/checkout.html">Checkout Instructions</a> page.',
                max_length=40,
                verbose_name="Do you intend to complete The Carpentries checkout process to be certified as a Carpentries Instructor?",
            ),
        ),
        migrations.AddField(
            model_name="trainingrequest",
            name="teaching_intent",
            field=models.CharField(
                choices=[
                    (
                        "yes-local",
                        "Yes - I plan to teach Carpentries workshops in my local community or personal networks",
                    ),
                    (
                        "yes-central",
                        "Yes - I plan to volunteer with The Carpentries to teach workshops for other communities",
                    ),
                    ("yes-either", "Yes - either or both of the above"),
                    ("no", "No"),
                    ("unsure", "Not sure"),
                ],
                default="unsure",
                max_length=40,
                verbose_name="Do you intend to teach Carpentries workshops within the next 12 months?",
            ),
        ),
        migrations.AlterField(
            model_name="trainingrequest",
            name="teaching_frequency_expectation",
            field=models.CharField(
                choices=[
                    ("not-at-all", "Not at all"),
                    ("yearly", "Once a year"),
                    ("monthly", "Several times a year"),
                    ("other", "Other:"),
                ],
                default="not-at-all",
                help_text=None,
                max_length=40,
                verbose_name="How often would you expect to teach Carpentries workshops  (of any kind) after this training?",
            ),
        ),
    ]