from datetime import date, datetime
from functools import partial

from django.urls import reverse

from trainings.filters import filter_trainees_by_instructor_status
from trainings.views import all_trainees_queryset
from workshops.models import (
    Award,
    Event,
    Organization,
    Person,
    Role,
    Tag,
    TrainingProgress,
    TrainingRequirement,
)
from workshops.tests.base import TestBase


class TestTraineesView(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpAirports()
        self._setUpNonInstructors()
        self._setUpTags()
        self._setUpRoles()

        self.training = TrainingRequirement.objects.get(name="Training")
        self.lesson_contribution, _ = TrainingRequirement.objects.get_or_create(
            name="Lesson Contribution", defaults={"url_required": True}
        )
        self.discussion = TrainingRequirement.objects.get(name="Discussion")

        self.ttt_event = Event.objects.create(
            start=datetime(2018, 7, 14),
            slug="2018-07-14-training",
            host=Organization.objects.first(),
        )
        self.ttt_event.tags.add(Tag.objects.get(name="TTT"))

    def test_view_loads(self):
        rv = self.client.get(reverse("all_trainees"))
        self.assertEqual(rv.status_code, 200)

    def test_bulk_add_progress(self):
        TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.discussion, state="n"
        )
        data = {
            "trainees": [self.spiderman.pk, self.ironman.pk],
            "requirement": self.discussion.pk,
            "state": "a",
            "submit": "",
        }

        # all trainees need to have a training task to assign a training
        # progress to them
        self.ironman.task_set.create(
            event=self.ttt_event,
            role=Role.objects.get(name="learner"),
        )
        self.spiderman.task_set.create(
            event=self.ttt_event,
            role=Role.objects.get(name="learner"),
        )

        rv = self.client.post(reverse("all_trainees"), data, follow=True)

        self.assertEqual(rv.resolver_match.view_name, "all_trainees")
        msg = "Successfully changed progress of all selected trainees."
        self.assertContains(rv, msg)
        got = set(
            TrainingProgress.objects.values_list(
                "trainee", "requirement", "state", "evaluated_by"
            )
        )
        expected = {
            (self.spiderman.pk, self.discussion.pk, "n", None),
            (self.spiderman.pk, self.discussion.pk, "a", self.admin.pk),
            (self.ironman.pk, self.discussion.pk, "a", self.admin.pk),
        }
        self.assertEqual(got, expected)

    def test_bulk_discard_progress(self):
        spiderman_progress = TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.discussion, state="n"
        )
        ironman_progress = TrainingProgress.objects.create(
            trainee=self.ironman, requirement=self.discussion, state="n"
        )
        blackwidow_progress = TrainingProgress.objects.create(
            trainee=self.blackwidow, requirement=self.discussion, state="n"
        )
        data = {
            "trainees": [self.spiderman.pk, self.ironman.pk],
            "discard": "",
        }
        rv = self.client.post(reverse("all_trainees"), data, follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "all_trainees")
        msg = "Successfully discarded progress of all selected trainees."
        self.assertContains(rv, msg)
        spiderman_progress.refresh_from_db()
        self.assertTrue(spiderman_progress.discarded)
        ironman_progress.refresh_from_db()
        self.assertTrue(ironman_progress.discarded)
        blackwidow_progress.refresh_from_db()
        self.assertFalse(blackwidow_progress.discarded)


class TestFilterTraineesByInstructorStatus(TestBase):
    def _setUpPermissions(self):
        pass

    def _setUpNonInstructors(self):
        pass

    def _setUpTrainingRequirements(self):
        """Add some Training Requirements created through fixture
        (amy/trainings/fixtures/training_requirements.json)"""
        self.demo, _ = TrainingRequirement.objects.get_or_create(
            name="Demo", defaults={"url_required": True}
        )
        self.lesson_contribution, _ = TrainingRequirement.objects.get_or_create(
            name="Lesson Contribution", defaults={}
        )

        self.discussion = TrainingRequirement.objects.get(name="Discussion")
        self.training = TrainingRequirement.objects.get(name="Training")

    def _setUpInstructors(self):
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
                    evaluated_by=None,
                    requirement=self.training,
                    state="p",  # passed
                ),
                TrainingProgress(
                    trainee=self.trainee1,
                    evaluated_by=None,
                    requirement=self.discussion,
                    state="p",
                ),
                TrainingProgress(
                    trainee=self.trainee1,
                    evaluated_by=None,
                    requirement=self.lesson_contribution,
                    state="p",
                ),
                TrainingProgress(
                    trainee=self.trainee1,
                    evaluated_by=None,
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
                    evaluated_by=None,
                    requirement=self.training,
                    state="p",  # passed
                ),
                TrainingProgress(
                    trainee=self.trainee2,
                    evaluated_by=None,
                    requirement=self.discussion,
                    state="p",
                ),
                TrainingProgress(
                    trainee=self.trainee2,
                    evaluated_by=None,
                    requirement=self.lesson_contribution,
                    state="p",
                ),
                TrainingProgress(
                    trainee=self.trainee2,
                    evaluated_by=None,
                    requirement=self.demo,
                    state="p",
                ),
            ]
        )
        Award.objects.create(
            person=self.trainee2, badge=self.instructor_badge, awarded=date(2014, 1, 1)
        )
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
                    evaluated_by=None,
                    requirement=self.training,
                    state="p",  # passed
                ),
                TrainingProgress(
                    trainee=self.trainee3,
                    evaluated_by=None,
                    requirement=self.discussion,
                    state="f",  # failed
                    notes="Failed",
                ),
                TrainingProgress(
                    trainee=self.trainee3,
                    evaluated_by=None,
                    requirement=self.lesson_contribution,
                    state="p",
                ),
                TrainingProgress(
                    trainee=self.trainee3,
                    evaluated_by=None,
                    requirement=self.demo,
                    state="p",
                ),
            ]
        )

    def setUp(self):
        self._setUpTrainingRequirements()
        super().setUp()

        # `filter_trainees_by_instructor_status` takes 3 parameters (queryset,
        # name and choice), but only 1 is used for tests (choice)
        self.queryset = all_trainees_queryset()
        self.filter = partial(
            filter_trainees_by_instructor_status, queryset=self.queryset, name=""
        )

    def test_no_choice(self):
        # result should be the same as original queryset
        rv = self.filter(choice="")
        self.assertEqual(rv, self.queryset)
        self.assertQuerysetEqual(rv, list(self.queryset), transform=lambda x: x)

    def test_instructors(self):
        # only instructors who have all 3 badges should be returned
        rv = self.filter(choice="yes")
        values = [self.instructor1, self.instructor2, self.instructor3]
        self.assertQuerysetEqual(rv, values, transform=lambda x: x)

    def test_eligible_trainees(self):
        # only 1 eligible trainee should be returned
        rv = self.filter(choice="eligible")
        values = [self.trainee1]
        self.assertQuerysetEqual(rv, values, transform=lambda x: x)

    def test_eligibility_query(self):
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
                passed_discussion=1,
                passed_lesson_contribution=1,
                passed_demo=1,
                instructor_eligible=1,
            ),
            # self.trainee2
            dict(
                username="trainee2_trainee2",
                is_instructor=4,
                passed_training=1,
                passed_discussion=1,
                passed_lesson_contribution=1,
                passed_demo=1,
                instructor_eligible=1,
            ),
            # self.trainee3
            dict(
                username="trainee3_trainee3",
                is_instructor=0,
                passed_training=1,
                passed_discussion=0,
                passed_lesson_contribution=1,
                passed_demo=1,
                instructor_eligible=0,
            ),
        ]
        for person, conditions in zip(rv, conditions_per_person):
            for k, v in conditions.items():
                self.assertEqual(
                    getattr(person, k),
                    v,
                    f"{person.username} attr {k} doesn't have value {v}",
                )

    def test_no_instructors(self):
        # only non-instructors should be returned
        rv = self.filter(choice="no")
        values = [self.trainee1, self.trainee3]
        self.assertQuerysetEqual(rv, values, transform=lambda x: x)
