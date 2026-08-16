from datetime import date
from typing import Any

from django_test_migrations.contrib.unittest_case import MigratorTestCase


class BaseMigrationTestCase(MigratorTestCase):
    def prepare(self) -> None:
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

    def prepare(self) -> None:
        """Prepare some data before the migration."""
        super().prepare()

        TrainingProgress = self.old_state.apps.get_model("workshops", "TrainingProgress")
        TrainingRequirement = self.old_state.apps.get_model("workshops", "TrainingRequirement")

        # Discussion should exist from a previous migration
        discussion = TrainingRequirement.objects.get(name="Discussion")
        swc_demo, _ = TrainingRequirement.objects.get_or_create(name="SWC Demo")
        dc_demo, _ = TrainingRequirement.objects.get_or_create(name="DC Demo")
        lc_homework, _ = TrainingRequirement.objects.get_or_create(name="LC Homework")
        demo, _ = TrainingRequirement.objects.get_or_create(name="Demo", defaults={"url_required": False})
        contribution, _ = TrainingRequirement.objects.get_or_create(
            name="Lesson Contribution", defaults={"url_required": True}
        )

        TrainingProgress.objects.create(trainee=self.spiderman, requirement=discussion)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=swc_demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=dc_demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=lc_homework)
        TrainingProgress.objects.create(trainee=self.spiderman, requirement=demo)
        TrainingProgress.objects.create(trainee=self.spiderman, requirement=contribution)

    def test_workshops_0259_existing_requirements(self) -> None:
        # test that deprecated requirements have been removed

        TrainingRequirement = self.new_state.apps.get_model("workshops", "TrainingRequirement")
        TrainingProgress = self.new_state.apps.get_model("workshops", "TrainingProgress")

        # first migration step:
        # test that Discussion was renamed to Welcome Session
        with self.assertRaises(TrainingRequirement.DoesNotExist):
            TrainingRequirement.objects.get(name="Discussion")
        TrainingRequirement.objects.get(name="Welcome Session")
        self.assertEqual(
            TrainingProgress.objects.filter(requirement__name="Welcome Session").count(),
            1,
        )

        # second migration step:
        # test that progresses have been moved to the correct requirements
        for prefix in ["SWC", "DC", "LC"]:
            self.assertEqual(
                TrainingProgress.objects.filter(requirement__name__startswith=prefix).count(),
                0,
            )
        self.assertEqual(TrainingProgress.objects.filter(requirement__name="Demo").count(), 3)
        self.assertEqual(
            TrainingProgress.objects.filter(requirement__name="Lesson Contribution").count(),
            2,
        )


class TestWorkshops0259NewRequirements(BaseMigrationTestCase):
    """
    Test the migration when generic 'Demo' and 'Lesson Contribution'
    TrainingRequirements do not exist already.
    """

    migrate_from = ("workshops", "0258_remove_trainingprogress_evaluated_by")
    migrate_to = ("workshops", "0259_remove_deprecated_training_requirements")

    def prepare(self) -> None:
        """Prepare some data before the migration."""
        super().prepare()

        TrainingProgress = self.old_state.apps.get_model("workshops", "TrainingProgress")
        TrainingRequirement = self.old_state.apps.get_model("workshops", "TrainingRequirement")

        swc_demo, _ = TrainingRequirement.objects.get_or_create(name="SWC Demo")
        dc_demo, _ = TrainingRequirement.objects.get_or_create(name="DC Demo")
        lc_homework, _ = TrainingRequirement.objects.get_or_create(name="LC Homework")

        TrainingProgress.objects.create(trainee=self.ironman, requirement=swc_demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=dc_demo)
        TrainingProgress.objects.create(trainee=self.ironman, requirement=lc_homework)

    def test_workshops_0259_new_requirements(self) -> None:
        TrainingRequirement = self.new_state.apps.get_model("workshops", "TrainingRequirement")
        TrainingProgress = self.new_state.apps.get_model("workshops", "TrainingProgress")

        # second migration step:
        # test that generic training requirements were created
        demo = TrainingRequirement.objects.get(name="Demo")
        contribution = TrainingRequirement.objects.get(name="Lesson Contribution")
        self.assertFalse(demo.url_required)
        self.assertTrue(contribution.url_required)

        # test that progresses have been moved to the correct generic requirements
        for prefix in ["SWC", "DC", "LC"]:
            self.assertEqual(
                TrainingProgress.objects.filter(requirement__name__startswith=prefix).count(),
                0,
            )
        self.assertEqual(TrainingProgress.objects.filter(requirement__name="Demo").count(), 2)
        self.assertEqual(
            TrainingProgress.objects.filter(requirement__name="Lesson Contribution").count(),
            1,
        )


class TestWorkshops0259Rollback(BaseMigrationTestCase):
    """Tests rolling back the migration."""

    migrate_from = ("workshops", "0259_remove_deprecated_training_requirements")
    migrate_to = ("workshops", "0258_remove_trainingprogress_evaluated_by")

    def prepare(self) -> None:
        """Prepare some data before the migration."""
        super().prepare()

        TrainingProgress = self.old_state.apps.get_model("workshops", "TrainingProgress")
        TrainingRequirement = self.old_state.apps.get_model("workshops", "TrainingRequirement")

        welcome = TrainingRequirement.objects.get(name="Welcome Session")
        TrainingProgress.objects.create(trainee=self.ironman, requirement=welcome)

    def test_workshops_0259_rollback(self) -> None:
        TrainingRequirement = self.new_state.apps.get_model("workshops", "TrainingRequirement")
        TrainingProgress = self.new_state.apps.get_model("workshops", "TrainingProgress")

        # second migration step rollback: nothing happens

        # first migration step rollback:
        # test that Discussion was renamed to Welcome Session
        with self.assertRaises(TrainingRequirement.DoesNotExist):
            TrainingRequirement.objects.get(name="Welcome Session")
        TrainingRequirement.objects.get(name="Discussion")
        self.assertEqual(
            TrainingProgress.objects.filter(requirement__name="Discussion").count(),
            1,
        )


class TestWorkshops0261(BaseMigrationTestCase):
    """
    Test the migration of lesson contributions.
    """

    migrate_from = ("workshops", "0260_add_involvement_types")
    migrate_to = ("workshops", "0261_migrate_lesson_contribution_to_get_involved")

    def prepare(self) -> None:
        """Prepare some data before the migration."""
        super().prepare()

        TrainingProgress = self.old_state.apps.get_model("workshops", "TrainingProgress")
        TrainingRequirement = self.old_state.apps.get_model("workshops", "TrainingRequirement")

        demo = TrainingRequirement.objects.get(name="Demo")
        contribution, _ = TrainingRequirement.objects.get_or_create(
            name="Lesson Contribution", defaults={"url_required": True}
        )

        TrainingProgress.objects.create(trainee=self.spiderman, requirement=demo)
        TrainingProgress.objects.create(
            trainee=self.ironman,
            requirement=contribution,
            url="example.org",
            notes="Some test notes",
        )

    def test_workshops_0261(self) -> None:
        TrainingRequirement = self.new_state.apps.get_model("workshops", "TrainingRequirement")
        TrainingProgress = self.new_state.apps.get_model("workshops", "TrainingProgress")
        Involvement = self.new_state.apps.get_model("trainings", "Involvement")

        # test that GitHub Contribution involvement was created
        contribution = Involvement.objects.get(name="GitHub Contribution")
        self.assertTrue(contribution.url_required)

        # test that Lesson Contribution was renamed to Get Involved
        get_involved = TrainingRequirement.objects.get(name="Get Involved")
        self.assertFalse(get_involved.url_required)
        self.assertTrue(get_involved.involvement_required)

        # test that progresses were properly migrated
        self.assertEqual(TrainingProgress.objects.filter(requirement__name="Get Involved").count(), 1)
        self.assertQuerySetEqual(
            TrainingProgress.objects.filter(requirement__name="Get Involved"),
            TrainingProgress.objects.filter(involvement_type__name="GitHub Contribution"),
        )

        progress = TrainingProgress.objects.get(trainee__pk=self.ironman.pk, requirement__name="Get Involved")
        self.assertEqual(progress.date, progress.created_at.date())
        self.assertIn(
            "Some test notes\nMigrated from Lesson Contribution on",
            progress.notes,
        )

        # test that other progress is unaffected
        demo_progress = TrainingProgress.objects.get(trainee__pk=self.spiderman.pk, requirement__name="Demo")
        self.assertIsNone(demo_progress.involvement_type)
        self.assertIsNone(demo_progress.date)
        self.assertEqual(demo_progress.notes, "")


class TestWorkshops0261Rollback(BaseMigrationTestCase):
    """
    Test the reverse migration of lesson contributions.
    """

    migrate_from = ("workshops", "0261_migrate_lesson_contribution_to_get_involved")
    migrate_to = ("workshops", "0260_add_involvement_types")

    def prepare(self) -> None:
        """Prepare some data before the migration."""
        super().prepare()

        TrainingProgress = self.old_state.apps.get_model("workshops", "TrainingProgress")
        TrainingRequirement = self.old_state.apps.get_model("workshops", "TrainingRequirement")
        Involvement = self.old_state.apps.get_model("trainings", "Involvement")

        demo = TrainingRequirement.objects.get(name="Demo")
        get_involved = TrainingRequirement.objects.get(name="Get Involved")
        contribution = Involvement.objects.get(name="GitHub Contribution")

        TrainingProgress.objects.create(trainee=self.spiderman, requirement=demo)
        TrainingProgress.objects.create(
            trainee=self.ironman,
            requirement=get_involved,
            involvement_type=contribution,
            date=date(2023, 5, 25),
            url="example.org",
            notes="Some test notes",
        )

    def test_workshops_0261_rollback(self) -> None:
        TrainingRequirement = self.new_state.apps.get_model("workshops", "TrainingRequirement")
        TrainingProgress = self.new_state.apps.get_model("workshops", "TrainingProgress")
        Involvement = self.new_state.apps.get_model("trainings", "Involvement")

        # test that Get Involved was renamed to Lesson Contribution
        get_involved = TrainingRequirement.objects.get(name="Lesson Contribution")
        self.assertTrue(get_involved.url_required)
        self.assertFalse(get_involved.involvement_required)

        # test that GitHub Contribution Involvement was removed
        self.assertEqual(Involvement.objects.filter(name="GitHub Contribution").count(), 0)

        # test that progresses were properly migrated
        self.assertEqual(
            TrainingProgress.objects.filter(requirement__name="Lesson Contribution").count(),
            1,
        )

        progress = TrainingProgress.objects.get(trainee__pk=self.ironman.pk, requirement__name="Lesson Contribution")
        self.assertIsNone(progress.involvement_type)
        self.assertEqual(progress.date, date(2023, 5, 25))  # date unchanged
        self.assertIn(
            "Some test notes\nMigrated from GitHub Contribution involvement on",
            progress.notes,
        )

        # test that other progress is unaffected
        demo_progress = TrainingProgress.objects.get(trainee__pk=self.spiderman.pk, requirement__name="Demo")
        self.assertIsNone(demo_progress.involvement_type)
        self.assertIsNone(demo_progress.date)
        self.assertEqual(demo_progress.notes, "")


class TestWorkshops0263Rollback(MigratorTestCase):
    migrate_from = ("workshops", "0263_remove_workshoprequest_number_attendees")
    migrate_to = (
        "workshops",
        "0262_alter_trainingrequest_training_completion_agreement",
    )

    def prepare(self) -> None:
        """Prepare some data before the migration."""
        # create some requests
        WorkshopRequest = self.old_state.apps.get_model("workshops", "WorkshopRequest")
        Language = self.old_state.apps.get_model("workshops", "Language")
        WorkshopRequest.objects.create(
            location="London",
            country="GB",
            language=Language.objects.get(name="English"),
            administrative_fee="nonprofit",
            travel_expences_agreement=True,
        )

    def test_workshops_0263_rollback(self) -> None:
        """Ensure the migration can be rolled back without an error."""
        WorkshopRequest = self.new_state.apps.get_model("workshops", "WorkshopRequest")
        request = WorkshopRequest.objects.get(location="London")
        self.assertEqual(request.number_attendees, "")


class TestWorkshops0300LinkTrainingRequestsToTasks(MigratorTestCase):
    """Every training task a person holds should end up linked to every accepted
    training request they hold, and to nothing else."""

    migrate_from = ("workshops", "0299_trainingrequest_tasks")
    migrate_to = ("workshops", "0300_link_training_requests_to_tasks")

    def create_person(self, username: str) -> Any:
        Person = self.old_state.apps.get_model("workshops", "Person")
        # `github` is unique and defaults to "", so it has to differ between people.
        return Person.objects.create(
            personal=username,
            family="Tester",
            username=username,
            country="US",
            github=username,
        )

    def create_request(self, person: Any, state: str) -> Any:
        TrainingRequest = self.old_state.apps.get_model("workshops", "TrainingRequest")
        return TrainingRequest.objects.create(
            person=person,
            state=state,
            personal=person.personal,
            family=person.family,
            email=f"{person.username}@example.org",
            affiliation="Test University",
            location="Cracow",
            country="PL",
            reason="Just for fun.",
        )

    def create_task(self, person: Any, event: Any, role: Any) -> Any:
        Task = self.old_state.apps.get_model("workshops", "Task")
        return Task.objects.create(person=person, event=event, role=role)

    def prepare(self) -> None:
        Event = self.old_state.apps.get_model("workshops", "Event")
        Organization = self.old_state.apps.get_model("workshops", "Organization")
        Role = self.old_state.apps.get_model("workshops", "Role")
        Tag = self.old_state.apps.get_model("workshops", "Tag")

        org = Organization.objects.create(domain="example.org", fullname="Test Org")
        ttt, _ = Tag.objects.get_or_create(name="TTT")
        learner, _ = Role.objects.get_or_create(name="learner")
        helper, _ = Role.objects.get_or_create(name="helper")

        self.ttt_event = Event.objects.create(slug="ttt-event", host=org)
        self.ttt_event.tags.add(ttt)
        self.other_ttt_event = Event.objects.create(slug="ttt-event-2", host=org)
        self.other_ttt_event.tags.add(ttt)
        self.non_ttt_event = Event.objects.create(slug="regular-event", host=org)

        # One task, one accepted request -> linked.
        simple = self.create_person("simple")
        self.simple_request = self.create_request(simple, "a")
        self.simple_task = self.create_task(simple, self.ttt_event, learner)

        # One task, one accepted request among discarded/pending ones -> only the
        # accepted one is linked.
        reapplied = self.create_person("reapplied")
        self.discarded_request = self.create_request(reapplied, "d")
        self.accepted_request = self.create_request(reapplied, "a")
        self.pending_request = self.create_request(reapplied, "p")
        self.reapplied_task = self.create_task(reapplied, self.ttt_event, learner)

        # One task, but the request was never accepted -> not linked.
        pending_only = self.create_person("pendingonly")
        self.pending_only_request = self.create_request(pending_only, "p")
        self.create_task(pending_only, self.ttt_event, learner)

        # One task, two accepted requests -> both linked to it.
        two_accepted = self.create_person("twoaccepted")
        self.first_accepted = self.create_request(two_accepted, "a")
        self.second_accepted = self.create_request(two_accepted, "a")
        self.shared_task = self.create_task(two_accepted, self.ttt_event, learner)

        # Two tasks, one accepted request -> both linked to it.
        two_tasks = self.create_person("twotasks")
        self.two_tasks_request = self.create_request(two_tasks, "a")
        self.first_task = self.create_task(two_tasks, self.ttt_event, learner)
        self.second_task = self.create_task(two_tasks, self.other_ttt_event, learner)

        # Tasks failing the role/tag conditions -> no link at all.
        wrong_role = self.create_person("wrongrole")
        self.wrong_role_request = self.create_request(wrong_role, "a")
        self.create_task(wrong_role, self.ttt_event, helper)

        wrong_tag = self.create_person("wrongtag")
        self.wrong_tag_request = self.create_request(wrong_tag, "a")
        self.create_task(wrong_tag, self.non_ttt_event, learner)

        # A request whose person never got a training task.
        self.unmatched_request = self.create_request(self.create_person("unmatched"), "a")

    def linked_tasks(self, request: Any) -> set[int]:
        TrainingRequest = self.new_state.apps.get_model("workshops", "TrainingRequest")
        return set(TrainingRequest.objects.get(pk=request.pk).tasks.values_list("pk", flat=True))

    def test_single_pair_is_linked(self) -> None:
        self.assertEqual(self.linked_tasks(self.simple_request), {self.simple_task.pk})

    def test_only_accepted_request_is_linked(self) -> None:
        self.assertEqual(self.linked_tasks(self.accepted_request), {self.reapplied_task.pk})
        self.assertEqual(self.linked_tasks(self.discarded_request), set())
        self.assertEqual(self.linked_tasks(self.pending_request), set())

    def test_request_never_accepted_is_left_alone(self) -> None:
        self.assertEqual(self.linked_tasks(self.pending_only_request), set())

    def test_one_task_is_linked_to_every_accepted_request(self) -> None:
        self.assertEqual(self.linked_tasks(self.first_accepted), {self.shared_task.pk})
        self.assertEqual(self.linked_tasks(self.second_accepted), {self.shared_task.pk})

    def test_every_task_is_linked_to_one_request(self) -> None:
        self.assertEqual(
            self.linked_tasks(self.two_tasks_request),
            {self.first_task.pk, self.second_task.pk},
        )

    def test_tasks_failing_role_or_tag_are_ignored(self) -> None:
        self.assertEqual(self.linked_tasks(self.wrong_role_request), set())
        self.assertEqual(self.linked_tasks(self.wrong_tag_request), set())

    def test_request_without_any_task_is_left_alone(self) -> None:
        self.assertEqual(self.linked_tasks(self.unmatched_request), set())
