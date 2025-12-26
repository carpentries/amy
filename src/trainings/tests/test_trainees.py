from datetime import date, datetime
from functools import partial
from html import escape

from django.urls import reverse

from src.trainings.filters import filter_trainees_by_instructor_status
from src.trainings.models import Involvement
from src.trainings.views import all_trainees_queryset
from src.workshops.models import (
    Award,
    Event,
    Organization,
    Person,
    Role,
    Tag,
    TrainingProgress,
    TrainingRequirement,
)
from src.workshops.tests.base import TestBase


class TestTraineesView(TestBase):
    def setUp(self) -> None:
        self._setUpUsersAndLogin()
        self._setUpNonInstructors()
        self._setUpTags()
        self._setUpRoles()

        self.training = TrainingRequirement.objects.get(name="Training")
        self.get_involved, _ = TrainingRequirement.objects.get_or_create(
            name="Get Involved", defaults={"involvement_required": True}
        )
        self.welcome = TrainingRequirement.objects.get(name="Welcome Session")
        self.demo = TrainingRequirement.objects.get(name="Demo")
        self.involvement, _ = Involvement.objects.get_or_create(
            name="Workshop Instructor/Helper", defaults={"url_required": True}
        )

        self.ttt_event = Event.objects.create(
            start=datetime(2018, 7, 14),
            slug="2018-07-14-training",
            host=Organization.objects.all()[0],
        )
        self.ttt_event.tags.add(Tag.objects.get(name="TTT"))

        # add some training tasks
        self.ironman.task_set.create(
            event=self.ttt_event,
            role=Role.objects.get(name="learner"),
        )
        self.spiderman.task_set.create(
            event=self.ttt_event,
            role=Role.objects.get(name="learner"),
        )

    def test_view_loads(self) -> None:
        rv = self.client.get(reverse("all_trainees"))
        self.assertEqual(rv.status_code, 200)

    def test_bulk_add_progress__welcome(self) -> None:
        # Arrange
        # create a pre-existing progress to ensure bulk adding doesn't interfere
        TrainingProgress.objects.create(trainee=self.spiderman, requirement=self.welcome, state="n")
        data = {
            "trainees": [self.spiderman.pk, self.ironman.pk],
            "requirement": self.welcome.pk,
            "state": "a",
            "submit": "",
        }

        # Act
        rv = self.client.post(reverse("all_trainees"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainees")
        msg = "Successfully changed progress of all selected trainees."
        self.assertContains(rv, msg)

        got = set(TrainingProgress.objects.values_list("trainee", "requirement", "state"))
        expected = {
            (self.spiderman.pk, self.welcome.pk, "n"),
            (self.spiderman.pk, self.welcome.pk, "a"),
            (self.ironman.pk, self.welcome.pk, "a"),
        }
        self.assertEqual(got, expected)

    def test_bulk_add_progress__training(self) -> None:
        # Arrange
        # create a pre-existing progress to ensure bulk adding doesn't interfere
        TrainingProgress.objects.create(trainee=self.spiderman, requirement=self.training, state="n")
        data = {
            "trainees": [self.spiderman.pk, self.ironman.pk],
            "requirement": self.training.pk,
            "state": "a",
            "event": self.ttt_event.pk,
            "submit": "",
        }

        # Act
        rv = self.client.post(reverse("all_trainees"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainees")
        msg = "Successfully changed progress of all selected trainees."
        self.assertContains(rv, msg)

        got = set(TrainingProgress.objects.values_list("trainee", "requirement", "state"))
        expected = {
            (self.spiderman.pk, self.training.pk, "n"),
            (self.spiderman.pk, self.training.pk, "a"),
            (self.ironman.pk, self.training.pk, "a"),
        }
        self.assertEqual(got, expected)

    def test_bulk_add_progress__training_with_failures(self) -> None:
        # Arrange
        # Intended result:
        # spiderman: pass
        # ironman: fail due to existing progress for this event
        # blackwidow: fail due to no learner task for this event
        TrainingProgress.objects.create(
            trainee=self.ironman,
            requirement=self.training,
            state="n",
            event=self.ttt_event,
        )
        data = {
            "trainees": [self.spiderman.pk, self.ironman.pk, self.blackwidow.pk],
            "requirement": self.training.pk,
            "state": "a",
            "event": self.ttt_event.pk,
            "submit": "",
        }

        # Act
        rv = self.client.post(reverse("all_trainees"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainees")

        msgs = [
            (f"Trainee {escape(str(self.ironman))} already has a training progress for event {self.ttt_event}."),
            (f"Trainee {escape(str(self.blackwidow))} does not have a learner task for event {self.ttt_event}."),
            ("Changed progress of 1 trainee(s). 2 trainee(s) were skipped due to errors."),
        ]
        for msg in msgs:
            self.assertContains(rv, msg)

        got = set(TrainingProgress.objects.values_list("trainee", "requirement", "state"))
        expected = {
            (self.spiderman.pk, self.training.pk, "a"),  # new
            (self.ironman.pk, self.training.pk, "n"),  # pre-existing
        }
        self.assertEqual(got, expected)

    def test_bulk_add_progress__demo(self) -> None:
        # Arrange
        # create a pre-existing progress to ensure bulk adding doesn't interfere
        TrainingProgress.objects.create(trainee=self.spiderman, requirement=self.demo, state="n")
        data = {
            "trainees": [self.spiderman.pk, self.ironman.pk],
            "requirement": self.demo.pk,
            "state": "a",
            "submit": "",
        }

        # Act
        rv = self.client.post(reverse("all_trainees"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainees")
        msg = "Successfully changed progress of all selected trainees."
        self.assertContains(rv, msg)

        got = set(TrainingProgress.objects.values_list("trainee", "requirement", "state"))
        expected = {
            (self.spiderman.pk, self.demo.pk, "n"),
            (self.spiderman.pk, self.demo.pk, "a"),
            (self.ironman.pk, self.demo.pk, "a"),
        }
        self.assertEqual(got, expected)

    def test_bulk_add_progress__get_involved(self) -> None:
        # Arrange
        # create a pre-existing progress to ensure bulk adding doesn't interfere
        TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=self.get_involved,
            state="n",
            involvement_type=self.involvement,
            url="https://example.org",
            date=date(2022, 5, 3),
        )
        data = {
            "trainees": [self.spiderman.pk, self.ironman.pk],
            "requirement": self.get_involved.pk,
            "state": "a",
            "involvement_type": self.involvement.pk,
            "url": "https://example.org",
            "date": "2023-6-21",
            "submit": "",
        }

        # Act
        rv = self.client.post(reverse("all_trainees"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainees")
        msg = "Successfully changed progress of all selected trainees."
        self.assertContains(rv, msg)

        got = set(TrainingProgress.objects.values_list("trainee", "requirement", "state"))
        expected = {
            (self.spiderman.pk, self.get_involved.pk, "n"),
            (self.spiderman.pk, self.get_involved.pk, "a"),
            (self.ironman.pk, self.get_involved.pk, "a"),
        }
        self.assertEqual(got, expected)


class TestFilterTraineesByInstructorStatus(TestBase):
    def _setUpPermissions(self) -> None:
        pass

    def _setUpNonInstructors(self) -> None:
        pass

    def _setUpTrainingRequirements(self) -> None:
        """Add some Training Requirements created through seeding
        (amy/scripts/seed_training_requirements.py)"""
        self.demo, _ = TrainingRequirement.objects.get_or_create(name="Demo", defaults={"url_required": True})
        self.get_involved, _ = TrainingRequirement.objects.get_or_create(name="Get Involved", defaults={})

        self.welcome = TrainingRequirement.objects.get(name="Welcome Session")
        self.training = TrainingRequirement.objects.get(name="Training")
        self.involvement, _ = Involvement.objects.get_or_create(name="Test Involvement", defaults={})

    def _setUpInstructors(self) -> None:
        # prepare data

        # 1 SWC/DC/LC instructor
        self.instructor1 = Person.objects.create(
            personal="Instructor1",
            family="Instructor1",
            email="instructor1@example.org",
            username="instructor1_instructor1",
        )
        Award.objects.create(
            person=self.instructor1,
            badge=self.instructor_badge,
            awarded=date(2014, 1, 1),
        )
        self.instructor2 = Person.objects.create(
            personal="Instructor2",
            family="Instructor2",
            email="instructor2@example.org",
            username="instructor2_instructor2",
        )
        Award.objects.create(
            person=self.instructor2,
            badge=self.instructor_badge,
            awarded=date(2014, 1, 1),
        )
        self.instructor3 = Person.objects.create(
            personal="Instructor3",
            family="Instructor3",
            email="instructor3@example.org",
            username="instructor3_instructor3",
        )
        Award.objects.create(
            person=self.instructor3,
            badge=self.instructor_badge,
            awarded=date(2014, 1, 1),
        )

        # 1 eligible trainee with no instructor badges
        self.trainee1 = Person.objects.create(
            personal="Trainee1",
            family="Trainee1",
            email="trainee1@example.org",
            username="trainee1_trainee1",
        )
        TrainingProgress.objects.bulk_create(
            [
                TrainingProgress(
                    trainee=self.trainee1,
                    requirement=self.training,
                    state="p",  # passed
                ),
                TrainingProgress(
                    trainee=self.trainee1,
                    requirement=self.welcome,
                    state="p",
                ),
                TrainingProgress(
                    trainee=self.trainee1,
                    requirement=self.get_involved,
                    involvement_type=self.involvement,
                    date=date(2023, 6, 1),
                    state="p",
                ),
                TrainingProgress(
                    trainee=self.trainee1,
                    requirement=self.demo,
                    state="p",
                ),
            ]
        )
        # 1 eligible trainee with instructor badge
        self.trainee2 = Person.objects.create(
            personal="Trainee2",
            family="Trainee2",
            email="trainee2@example.org",
            username="trainee2_trainee2",
        )
        TrainingProgress.objects.bulk_create(
            [
                TrainingProgress(
                    trainee=self.trainee2,
                    requirement=self.training,
                    state="p",  # passed
                ),
                TrainingProgress(
                    trainee=self.trainee2,
                    requirement=self.welcome,
                    state="p",
                ),
                TrainingProgress(
                    trainee=self.trainee2,
                    requirement=self.get_involved,
                    involvement_type=self.involvement,
                    date=date(2023, 6, 1),
                    state="p",
                ),
                TrainingProgress(
                    trainee=self.trainee2,
                    requirement=self.demo,
                    state="p",
                ),
            ]
        )
        Award.objects.create(person=self.trainee2, badge=self.instructor_badge, awarded=date(2014, 1, 1))
        # 1 non-eligible trainee
        self.trainee3 = Person.objects.create(
            personal="Trainee3",
            family="Trainee3",
            email="trainee3@example.org",
            username="trainee3_trainee3",
        )
        TrainingProgress.objects.bulk_create(
            [
                TrainingProgress(
                    trainee=self.trainee3,
                    requirement=self.training,
                    state="p",  # passed
                ),
                TrainingProgress(
                    trainee=self.trainee3,
                    requirement=self.welcome,
                    state="f",  # failed
                    notes="Failed",
                ),
                TrainingProgress(
                    trainee=self.trainee3,
                    requirement=self.get_involved,
                    involvement_type=self.involvement,
                    date=date(2023, 6, 1),
                    state="p",
                ),
                TrainingProgress(
                    trainee=self.trainee3,
                    requirement=self.demo,
                    state="p",
                ),
            ]
        )

    def setUp(self) -> None:
        self._setUpTrainingRequirements()
        super().setUp()

        # `filter_trainees_by_instructor_status` takes 3 parameters (queryset,
        # name and choice), but only 1 is used for tests (choice)
        self.queryset = all_trainees_queryset()
        self.filter = partial(filter_trainees_by_instructor_status, queryset=self.queryset, name="")

    def test_no_choice(self) -> None:
        # result should be the same as original queryset
        rv = self.filter(choice="")
        self.assertEqual(rv, self.queryset)
        self.assertQuerySetEqual(rv, list(self.queryset), transform=lambda x: x)

    def test_instructors(self) -> None:
        # only instructors who have all 3 badges should be returned
        rv = self.filter(choice="yes")
        values = [self.instructor1, self.instructor2, self.instructor3]
        self.assertQuerySetEqual(rv, values, transform=lambda x: x)

    def test_eligible_trainees(self) -> None:
        # only 1 eligible trainee should be returned
        rv = self.filter(choice="eligible")
        values = [self.trainee1]
        self.assertQuerySetEqual(rv, values, transform=lambda x: x)

    def test_eligibility_query(self) -> None:
        # check if eligibility query works correctly
        self.assertEqual(Person.objects.all().count(), 6)
        rv = all_trainees_queryset().order_by("pk")
        conditions_per_person = [
            # self.instructor1
            dict(
                username="instructor1_instructor1",
                is_instructor=1,
                instructor_eligible=0,
            ),
            # self.instructor2
            dict(
                username="instructor2_instructor2",
                is_instructor=1,
                instructor_eligible=0,
            ),
            # self.instructor3
            dict(
                username="instructor3_instructor3",
                is_instructor=1,
                instructor_eligible=0,
            ),
            # self.trainee1
            dict(
                username="trainee1_trainee1",
                is_instructor=0,
                passed_training=1,
                passed_welcome=1,
                passed_get_involved=1,
                passed_demo=1,
                instructor_eligible=1,
            ),
            # self.trainee2
            dict(
                username="trainee2_trainee2",
                is_instructor=4,
                passed_training=1,
                passed_welcome=1,
                passed_get_involved=1,
                passed_demo=1,
                instructor_eligible=1,
            ),
            # self.trainee3
            dict(
                username="trainee3_trainee3",
                is_instructor=0,
                passed_training=1,
                passed_welcome=0,
                passed_get_involved=1,
                passed_demo=1,
                instructor_eligible=0,
            ),
        ]
        for person, conditions in zip(rv, conditions_per_person, strict=False):
            for k, v in conditions.items():
                self.assertEqual(
                    getattr(person, k),
                    v,
                    f"{person.username} attr {k} doesn't have value {v}",
                )

    def test_no_instructors(self) -> None:
        # only non-instructors should be returned
        rv = self.filter(choice="no")
        values = [self.trainee1, self.trainee3]
        self.assertQuerySetEqual(rv, values, transform=lambda x: x)
