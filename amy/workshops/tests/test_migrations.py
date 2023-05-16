from django_test_migrations.contrib.unittest_case import MigratorTestCase


class TestDirectMigration(MigratorTestCase):
    """This class is used to test direct migrations."""

    migrate_from = ("workshops", "0257_alter_membership_variant")
    migrate_to = ("workshops", "0258_remove_deprecated_training_requirements")

    def prepare(self):
        """Prepare some data before the migration."""
        # create some Persons
        Person = self.old_state.apps.get_model("workshops", "Person")
        self.spiderman, _ = Person.objects.get_or_create(
            personal="Peter",
            middle="Q.",
            family="Parker",
            email="peter@webslinger.net",
            gender="O",
            gender_other="Spider",
            username="spiderman",
            country="US",
        )

        self.ironman, _ = Person.objects.get_or_create(
            personal="Tony",
            family="Stark",
            email="me@stark.com",
            gender="M",
            username="ironman",
            country="US",
        )

        self.blackwidow = Person.objects.create(
            personal="Natasha",
            family="Romanova",
            email=None,
            gender="F",
            username="blackwidow",
            country="RU",
        )

        TrainingProgress = self.old_state.apps.get_model(
            "workshops", "TrainingProgress"
        )
        TrainingRequirement = self.old_state.apps.get_model(
            "workshops", "TrainingRequirement"
        )

        swc_demo, _ = TrainingRequirement.objects.get_or_create(name="SWC Demo")
        dc_demo, _ = TrainingRequirement.objects.get_or_create(name="DC Demo")
        lc_homework, _ = TrainingRequirement.objects.get_or_create(name="LC Homework")
        self.demo, _ = TrainingRequirement.objects.get_or_create(
            name="Demo", url_required=False
        )
        self.contribution, _ = TrainingRequirement.objects.get_or_create(
            name="Lesson Contribution", url_required=True
        )

        TrainingProgress.objects.create(trainee=self.ironman, requirement=swc_demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=dc_demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=lc_homework)
        TrainingProgress.objects.create(trainee=self.spiderman, requirement=self.demo)
        TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.contribution
        )

    def test_migration_workshops0258(self):
        """Run the test itself."""
        TrainingProgress = self.new_state.apps.get_model(
            "workshops", "TrainingProgress"
        )

        assert (
            TrainingProgress.objects.filter(requirement__name__startswith="SWC").count()
            == 0
        )
        assert (
            TrainingProgress.objects.filter(requirement__name__startswith="DC").count()
            == 0
        )
        assert (
            TrainingProgress.objects.filter(requirement__name__startswith="LC").count()
            == 0
        )
        assert TrainingProgress.objects.filter(requirement__name="Demo").count() == 3
        assert (
            TrainingProgress.objects.filter(
                requirement__name="Lesson Contribution"
            ).count()
            == 2
        )
