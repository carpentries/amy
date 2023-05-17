from django_test_migrations.contrib.unittest_case import MigratorTestCase


class BaseMigrationTestCase(MigratorTestCase):
    def prepare(self):
        """Prepare some data before the migration."""
        # create some Persons
        Person = self.old_state.apps.get_model("workshops", "Person")
        self.spiderman, _ = Person.objects.get_or_create(
            personal="Peter",
            family="Parker",
            defaults={
                "middle": "Q.",
                "email": "peter@webslinger.net",
                "gender": "O",
                "gender_other": "Spider",
                "username": "spiderman",
                "country": "US",
                "github": "spiderman",
            },
        )

        self.ironman, _ = Person.objects.get_or_create(
            personal="Tony",
            family="Stark",
            defaults={
                "email": "me@stark.com",
                "gender": "M",
                "username": "ironman",
                "github": "ironman",
                "country": "US",
            },
        )

        self.blackwidow = Person.objects.get_or_create(
            personal="Natasha",
            family="Romanova",
            defaults={
                "email": None,
                "gender": "F",
                "username": "blackwidow",
                "github": "blackwidow",
                "country": "RU",
            },
        )


class TestWorkshops0259ExistingRequirements(BaseMigrationTestCase):
    """
    Test the migration when generic 'Demo' and 'Lesson Contribution'
    TrainingRequirements are already present.
    """

    migrate_from = ("workshops", "0258_remove_trainingprogress_evaluated_by")
    migrate_to = ("workshops", "0259_remove_deprecated_training_requirements")

    def prepare(self):
        """Prepare some data before the migration."""
        super().prepare()

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
            name="Demo", defaults={"url_required": False}
        )
        self.contribution, _ = TrainingRequirement.objects.get_or_create(
            name="Lesson Contribution", defaults={"url_required": True}
        )

        TrainingProgress.objects.create(trainee=self.ironman, requirement=swc_demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=dc_demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=lc_homework)
        TrainingProgress.objects.create(trainee=self.spiderman, requirement=self.demo)
        TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.contribution
        )

    def test_workshops_0259_existing_requirements(self):
        # test that deprecated requirements have been removed

        TrainingRequirement = self.new_state.apps.get_model(
            "workshops", "TrainingRequirement"
        )
        for item in [
            "SWC Demo",
            "SWC Homework",
            "DC Demo",
            "DC Homework",
            "LC Demo",
            "LC Homework",
        ]:
            with self.assertRaises(TrainingRequirement.DoesNotExist):
                TrainingRequirement.objects.get(name=item)

        # test that progresses have been moved to the generic requirements
        TrainingProgress = self.new_state.apps.get_model(
            "workshops", "TrainingProgress"
        )

        for prefix in ["SWC", "DC", "LC"]:
            self.assertEqual(
                TrainingProgress.objects.filter(
                    requirement__name__startswith=prefix
                ).count(),
                0,
            )

        self.assertEqual(
            TrainingProgress.objects.filter(requirement__name="Demo").count(), 3
        )
        self.assertEqual(
            TrainingProgress.objects.filter(
                requirement__name="Lesson Contribution"
            ).count(),
            2,
        )


class TestWorkshops0259NewRequirements(BaseMigrationTestCase):
    """
    Test the migration when generic 'Demo' and 'Lesson Contribution'
    TrainingRequirements do not exist already.
    """

    migrate_from = ("workshops", "0258_remove_trainingprogress_evaluated_by")
    migrate_to = ("workshops", "0259_remove_deprecated_training_requirements")

    def prepare(self):
        """Prepare some data before the migration."""
        super().prepare()

        TrainingProgress = self.old_state.apps.get_model(
            "workshops", "TrainingProgress"
        )
        TrainingRequirement = self.old_state.apps.get_model(
            "workshops", "TrainingRequirement"
        )

        swc_demo, _ = TrainingRequirement.objects.get_or_create(name="SWC Demo")
        dc_demo, _ = TrainingRequirement.objects.get_or_create(name="DC Demo")
        lc_homework, _ = TrainingRequirement.objects.get_or_create(name="LC Homework")

        TrainingProgress.objects.create(trainee=self.ironman, requirement=swc_demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=dc_demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=lc_homework)

    def test_workshops_0259_new_requirements(self):
        # test that generic requirements were created
        TrainingRequirement = self.new_state.apps.get_model(
            "workshops", "TrainingRequirement"
        )

        demo = TrainingRequirement.objects.get(name="Demo")
        contribution = TrainingRequirement.objects.get(name="Lesson Contribution")
        self.assertFalse(demo.url_required)
        self.assertTrue(contribution.url_required)

        # test that deprecated requirements have been removed
        for item in [
            "SWC Demo",
            "SWC Homework",
            "DC Demo",
            "DC Homework",
            "LC Demo",
            "LC Homework",
        ]:
            with self.assertRaises(TrainingRequirement.DoesNotExist):
                TrainingRequirement.objects.get(name=item)

        # test that progresses have been moved to the generic requirements
        TrainingProgress = self.new_state.apps.get_model(
            "workshops", "TrainingProgress"
        )

        for prefix in ["SWC", "DC", "LC"]:
            self.assertEqual(
                TrainingProgress.objects.filter(
                    requirement__name__startswith=prefix
                ).count(),
                0,
            )

        self.assertEqual(
            TrainingProgress.objects.filter(requirement__name="Demo").count(), 2
        )
        self.assertEqual(
            TrainingProgress.objects.filter(
                requirement__name="Lesson Contribution"
            ).count(),
            1,
        )


class TestWorkshops0259Rollback(BaseMigrationTestCase):
    """Tests rolling back the migration."""

    migrate_from = ("workshops", "0259_remove_deprecated_training_requirements")
    migrate_to = ("workshops", "0258_remove_trainingprogress_evaluated_by")

    def prepare(self):
        """Prepare some data before the migration."""
        super().prepare()

        TrainingProgress = self.old_state.apps.get_model(
            "workshops", "TrainingProgress"
        )
        TrainingRequirement = self.old_state.apps.get_model(
            "workshops", "TrainingRequirement"
        )

        demo = TrainingRequirement.objects.get(name="Demo")
        contribution = TrainingRequirement.objects.get(name="Lesson Contribution")

        TrainingProgress.objects.create(trainee=self.ironman, requirement=demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=contribution)

    def test_workshops_0259_rollback(self):
        # test that deprecated requirements were added back in
        TrainingRequirement = self.new_state.apps.get_model(
            "workshops", "TrainingRequirement"
        )

        # all these requirements should exist
        for item in [
            "Demo",
            "Lesson Contribution",
            "SWC Demo",
            "SWC Homework",
            "DC Demo",
            "DC Homework",
            "LC Demo",
            "LC Homework",
        ]:
            TrainingRequirement.objects.get(name=item)

        # test that progresses were not changed
        TrainingProgress = self.new_state.apps.get_model(
            "workshops", "TrainingProgress"
        )

        for prefix in ["SWC", "DC", "LC"]:
            self.assertEqual(
                TrainingProgress.objects.filter(
                    requirement__name__startswith=prefix
                ).count(),
                0,
            )

        self.assertEqual(
            TrainingProgress.objects.filter(requirement__name="Demo").count(), 1
        )
        self.assertEqual(
            TrainingProgress.objects.filter(
                requirement__name="Lesson Contribution"
            ).count(),
            1,
        )
