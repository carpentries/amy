import datetime
from uuid import UUID

from django.db import migrations
from django.db.backends.base.schema import BaseDatabaseSchemaEditor
from django.db.migrations.state import StateApps

INSTRUCTOR_TRAINING_BENEFIT_NAME = "Instructor Training"
FULL_DISCOUNT_NAME = "Full Discount"


def create_accounts_and_benefits_for_open_training_requests(
    apps: StateApps, schema_editor: BaseDatabaseSchemaEditor
) -> None:
    TrainingRequest = apps.get_model("workshops", "TrainingRequest")
    Account = apps.get_model("offering", "Account")
    AccountBenefit = apps.get_model("offering", "AccountBenefit")
    Benefit = apps.get_model("offering", "Benefit")
    AccountBenefitDiscount = apps.get_model("offering", "AccountBenefitDiscount")
    ContentType = apps.get_model("contenttypes", "ContentType")

    person_ct = ContentType.objects.get(app_label="workshops", model="person")
    benefit = Benefit.objects.get_or_create(
        name=INSTRUCTOR_TRAINING_BENEFIT_NAME,
        # Defaults copied from `seed_benefits.py`.
        defaults={
            "active": True,
            "id": UUID("641e0a4c-0626-43f8-ae4f-ccf507b87791"),
            "description": "Instructor Training default benefit",
            "unit_type": "seat",
            "credits": 1,
        },
    )
    discount = AccountBenefitDiscount.objects.get_or_create(
        name=FULL_DISCOUNT_NAME,
        # Defaults copied from `seed_account_benefit_discounts.py`.
        defaults={
            "id": UUID("b2c3d4e5-f6a7-8901-bcde-f12345678901"),
        },
    )

    # Get all open training requests with assigned person, excluding instructor training learners.
    open_requests = (
        TrainingRequest.objects.filter(
            state="a",  # "Accepted"
            person__isnull=False,
            member_code="",  # Open training
        )
        .exclude(
            # Exclude instructor training learners
            person__task__event__administrator__domain="carpentries.org",
            person__task__role__name="learner",
        )
        .select_related("person")
    )

    for training_request in open_requests:
        person = training_request.person

        account, _ = Account.objects.get_or_create(
            generic_relation_content_type=person_ct,
            generic_relation_pk=person.pk,
            defaults={"account_type": "individual"},
        )

        start_date = training_request.created_at.date()
        end_date = start_date + datetime.timedelta(days=365)

        AccountBenefit.objects.get_or_create(
            account=account,
            benefit=benefit,
            defaults={
                "discount": discount,
                "start_date": start_date,
                "end_date": end_date,
                "allocation": 1,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("offering", "0004_alter_accountowner_permission_type"),
        ("workshops", "0288_trainingrequest_airport_iata"),
    ]

    operations = [
        migrations.RunPython(
            create_accounts_and_benefits_for_open_training_requests,
            migrations.RunPython.noop,
        ),
    ]
