from datetime import datetime, timedelta
from itertools import product

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse

from src.workshops.models import (
    Event,
    Member,
    MemberRole,
    Membership,
    Organization,
    Person,
    Role,
    Tag,
    Task,
)
from src.workshops.tests.base import TestBase


class TestTask(TestBase):
    "Tests for the task model, its manager and views"

    def setUp(self) -> None:
        self.fixtures = {}

        self._setUpTags()
        self._setUpRoles()

        test_host = Organization.objects.create(domain="example.com", fullname="Test Organization")

        self.test_person_1 = Person.objects.create(personal="Test", family="Person1", username="person1")

        self.test_person_2 = Person.objects.create(personal="Test", family="Person2", username="person2")

        test_event_1 = Event.objects.create(
            start=datetime.now(),
            slug="test_event_1",
            host=test_host,
        )

        test_event_2 = Event.objects.create(
            start=datetime.now(),
            slug="test_event_2",
            host=test_host,
        )

        test_event_3 = Event.objects.create(
            start=datetime.now(),
            slug="test_event_3",
            host=test_host,
        )

        self.instructor = Role.objects.get(name="instructor")
        self.learner = Role.objects.get(name="learner")
        self.helper = Role.objects.get(name="helper")
        roles = [self.instructor, self.learner, self.helper]
        people = [self.test_person_1, self.test_person_2]

        for role, person in product(roles, people):
            Task.objects.create(person=person, role=role, event=test_event_3)

        test_role_1 = Role.objects.create(name="test_role_1")
        test_role_2 = Role.objects.create(name="test_role_2")

        test_task_1 = Task.objects.create(person=self.test_person_1, event=test_event_1, role=test_role_1)

        test_task_2 = Task.objects.create(person=self.test_person_2, event=test_event_2, role=test_role_2)

        self.fixtures["test_task_1"] = test_task_1
        self.fixtures["test_task_2"] = test_task_2

        # create 3 events: one without TTT tag, and two with; out of the two,
        # one is allowed to have open applications, the other is not.
        self.non_ttt_event = Event.objects.create(
            start=datetime.now(),
            slug="non-ttt-event",
            host=test_host,
        )
        self.non_ttt_event.tags.set(Tag.objects.filter(name__in=["SWC", "DC"]))
        self.ttt_event_open = Event.objects.create(
            start=datetime.now(),
            slug="ttt-event-open-app",
            host=test_host,
            open_TTT_applications=True,
        )
        self.ttt_event_open.tags.set(Tag.objects.filter(name__in=["DC", "TTT"]))
        self.ttt_event_non_open = Event.objects.create(
            start=datetime.now(),
            slug="ttt-event-closed-app",
            host=test_host,
            open_TTT_applications=False,
        )
        self.ttt_event_non_open.tags.set(Tag.objects.filter(name__in=["DC", "TTT"]))

        # create a membership
        self.membership = Membership.objects.create(
            variant="partner",
            agreement_start=datetime.now() - timedelta(weeks=4),
            agreement_end=datetime.now() + timedelta(weeks=4),
            contribution_type="financial",
            public_instructor_training_seats=1,
            inhouse_instructor_training_seats=1,
        )
        Member.objects.create(
            membership=self.membership,
            organization=test_host,
            role=MemberRole.objects.all()[0],
        )

        self._setUpUsersAndLogin()

    def test_task_detail_view_reachable_from_event_person_and_role_of_task(self) -> None:
        correct_task = self.fixtures["test_task_1"]
        response = self.client.get(reverse("task_details", args=[str(correct_task.id)]))
        assert response.context["task"].pk == correct_task.pk

    def test_add_duplicate_task(self) -> None:
        """Ensure that duplicate tasks cannot exist"""
        task_1 = self.fixtures["test_task_1"]
        with self.assertRaises(IntegrityError):
            Task.objects.create(
                event=task_1.event,
                person=task_1.person,
                role=task_1.role,
            )

    def test_task_edit_view_reachable_from_event_person_and_role_of_task(self) -> None:
        correct_task = self.fixtures["test_task_1"]
        url_kwargs = {"task_id": correct_task.id}
        response = self.client.get(reverse("task_edit", kwargs=url_kwargs))
        assert response.context["task"].pk == correct_task.pk

    def test_task_manager_roles_lookup(self) -> None:
        """Test TaskManager methods for looking up roles by names."""
        event = Event.objects.get(slug="test_event_3")
        instructors = event.task_set.instructors()
        learners = event.task_set.learners()
        helpers = event.task_set.helpers()
        tasks = event.task_set.all()

        assert set(tasks) == set(instructors) | set(learners) | set(helpers)

    def test_delete_task(self) -> None:
        """Make sure deleted task is longer accessible."""
        for task in Task.objects.all():
            rv = self.client.post(reverse("task_delete", args=[task.pk]))
            assert rv.status_code == 302

            with self.assertRaises(Task.DoesNotExist):
                Task.objects.get(pk=task.pk)

    def test_seats_validation(self) -> None:
        """Ensure events without TTT tag raise ValidationError on
        `seat_membership` and `seat_open_training` fields."""

        # first wrong task
        task1 = Task(
            event=self.non_ttt_event,
            person=self.test_person_1,
            role=self.learner,
            seat_membership=self.membership,
            seat_open_training=False,
        )
        # second wrong task
        task2 = Task(
            event=self.non_ttt_event,
            person=self.test_person_1,
            role=self.learner,
            seat_membership=None,
            seat_open_training=True,
        )

        with self.assertRaises(ValidationError) as cm:
            task1.full_clean()
        exception = cm.exception
        self.assertIn("seat_membership", exception.error_dict)
        self.assertNotIn("seat_open_training", exception.error_dict)

        with self.assertRaises(ValidationError) as cm:
            task2.full_clean()
        exception = cm.exception
        self.assertIn("seat_open_training", exception.error_dict)
        self.assertNotIn("seat_membership", exception.error_dict)

        # first good task
        task4 = Task(
            event=self.ttt_event_open,
            person=self.test_person_2,
            role=self.learner,
            seat_membership=self.membership,
            seat_open_training=False,
        )
        # second good task
        task5 = Task(
            event=self.ttt_event_open,
            person=self.test_person_2,
            role=self.learner,
            seat_membership=None,
            seat_open_training=True,
        )
        task4.full_clean()
        task5.full_clean()

    def test_no_remaining_seats_warnings_when_adding(self) -> None:
        """Ensure warnings about memberships with no remaining instructor training
        seats appear when new tasks are added."""
        # Arrange
        # `self.membership` is set up with only 1 seat for both public
        # and in-house instructor training seats

        data1 = {
            "task-event": self.ttt_event_open.pk,
            "task-person": self.test_person_1.pk,
            "task-role": self.learner.pk,
            "task-seat_membership": self.membership.pk,
            # "task-seat_public": True,
        }
        # data2 = {
        #     "task-event": self.ttt_event_open.pk,
        #     "task-person": self.test_person_2.pk,
        #     "task-role": self.learner.pk,
        #     "task-seat_membership": self.membership.pk,
        #     # "task-seat_public": False,
        # }

        # Act
        response1 = self.client.post(reverse("task_add"), data1, follow=True)
        # response2 = self.client.post(reverse("task_add"), data2, follow=True)

        # Assert
        self.assertEqual(response1.status_code, 200)
        # self.assertEqual(response2.status_code, 200)
        self.assertContains(
            response1,
            f"Membership &quot;{self.membership}&quot; has no public instructor training seats remaining.",
        )
        # self.assertContains(
        #     response2,
        #     f"Membership &quot;{self.membership}&quot; has no in-house instructor training seats remaining.",
        # )

    def test_exceeded_seats_warnings_when_adding(self) -> None:
        """Ensure warnings about memberships with exceeded instructor training
        seats appear when new tasks are added."""
        # Arrange
        self.membership.public_instructor_training_seats = 0
        self.membership.inhouse_instructor_training_seats = 0
        self.membership.save()

        data1 = {
            "task-event": self.ttt_event_open.pk,
            "task-person": self.test_person_1.pk,
            "task-role": self.learner.pk,
            "task-seat_membership": self.membership.pk,
            # "task-seat_public": True,
        }
        # data2 = {
        #     "task-event": self.ttt_event_open.pk,
        #     "task-person": self.test_person_2.pk,
        #     "task-role": self.learner.pk,
        #     "task-seat_membership": self.membership.pk,
        #     # "task-seat_public": False,
        # }

        # Act
        response1 = self.client.post(reverse("task_add"), data1, follow=True)
        # response2 = self.client.post(reverse("task_add"), data2, follow=True)

        # Assert
        self.assertEqual(response1.status_code, 200)
        # self.assertEqual(response2.status_code, 200)
        self.assertContains(
            response1,
            f"Membership &quot;{self.membership}&quot; is using more public "
            "training seats than it&#x27;s been allowed.",
        )
        # self.assertContains(
        #     response2,
        #     f"Membership &quot;{self.membership}&quot; is using more in-house "
        #     "training seats than it&#x27;s been allowed.",
        # )

    def test_no_remaining_seats_warnings_when_updating(self) -> None:
        """Ensure warnings about memberships with no remaining instructor training
        seats appear when existing tasks are edited."""
        # Arrange
        # `self.membership` is set up with only 1 seat for both public
        # and in-house instructor training seats

        task1 = Task.objects.create(
            event=self.ttt_event_open,
            person=self.test_person_1,
            role=self.learner,
            seat_membership=self.membership,
            seat_public=True,
        )
        assert task1.seat_membership  # for mypy
        # task2 = Task.objects.create(
        #     event=self.ttt_event_open,
        #     person=self.test_person_2,
        #     role=self.learner,
        #     seat_membership=self.membership,
        #     seat_public=False,
        # )
        # assert task2.seat_membership  # for mypy

        data1 = {
            "event": task1.event.pk,
            "person": task1.person.pk,
            "role": task1.role.pk,
            "seat_membership": task1.seat_membership.pk,
            "seat_public": task1.seat_public,
        }
        # data2 = {
        #     "event": task2.event.pk,
        #     "person": task2.person.pk,
        #     "role": task2.role.pk,
        #     "seat_membership": task2.seat_membership.pk,
        #     "seat_public": task2.seat_public,
        # }

        # Act
        response1 = self.client.post(reverse("task_edit", args=[task1.pk]), data1, follow=True)
        # response2 = self.client.post(reverse("task_edit", args=[task2.pk]), data2, follow=True)

        # Assert
        self.assertEqual(response1.status_code, 200)
        # self.assertEqual(response2.status_code, 200)
        self.assertContains(
            response1,
            f"Membership &quot;{self.membership}&quot; has no public instructor training seats remaining.",
        )
        # self.assertContains(
        #     response2,
        #     f"Membership &quot;{self.membership}&quot; has no in-house instructor training seats remaining.",
        # )

    def test_exceeded_seats_warnings_when_updating(self) -> None:
        """Ensure warnings about memberships with exceeded instructor training
        seats appear when existing tasks are edited."""
        # Arrange
        self.membership.public_instructor_training_seats = 0
        self.membership.inhouse_instructor_training_seats = 0
        self.membership.save()

        task1 = Task.objects.create(
            event=self.ttt_event_open,
            person=self.test_person_1,
            role=self.learner,
            seat_membership=self.membership,
            seat_public=True,
        )
        assert task1.seat_membership  # for mypy
        # task2 = Task.objects.create(
        #     event=self.ttt_event_open,
        #     person=self.test_person_2,
        #     role=self.learner,
        #     seat_membership=self.membership,
        #     seat_public=False,
        # )
        # assert task2.seat_membership  # for mypy

        data1 = {
            "event": task1.event.pk,
            "person": task1.person.pk,
            "role": task1.role.pk,
            "seat_membership": task1.seat_membership.pk,
            "seat_public": task1.seat_public,
        }
        # data2 = {
        #     "event": task2.event.pk,
        #     "person": task2.person.pk,
        #     "role": task2.role.pk,
        #     "seat_membership": task2.seat_membership.pk,
        #     "seat_public": task2.seat_public,
        # }

        # Act
        response1 = self.client.post(reverse("task_edit", args=[task1.pk]), data1, follow=True)
        # response2 = self.client.post(reverse("task_edit", args=[task2.pk]), data2, follow=True)

        # Assert
        self.assertEqual(response1.status_code, 200)
        # self.assertEqual(response2.status_code, 200)
        self.assertContains(
            response1,
            f"Membership &quot;{self.membership}&quot; is using more public "
            "training seats than it&#x27;s been allowed.",
        )
        # self.assertContains(
        #     response2,
        #     f"Membership &quot;{self.membership}&quot; is using more in-house "
        #     "training seats than it&#x27;s been allowed.",
        # )

    def test_open_applications_TTT(self) -> None:
        """Ensure events with TTT tag but without open application flag raise
        ValidationError on `seat_open_training` field."""
        # wrong task
        task1 = Task(
            event=self.ttt_event_non_open,
            person=self.test_person_1,
            role=self.learner,
            seat_membership=None,
            seat_open_training=True,
        )
        # good task
        task2 = Task(
            event=self.ttt_event_open,
            person=self.test_person_1,
            role=self.learner,
            seat_membership=None,
            seat_open_training=True,
        )

        with self.assertRaises(ValidationError) as cm:
            task1.full_clean()
        exception = cm.exception
        self.assertIn("seat_open_training", exception.error_dict)
        self.assertNotIn("seat_membership", exception.error_dict)

        task2.full_clean()

    def test_both_open_app_and_seat(self) -> None:
        """Ensure we cannot add a task with both options selected: a member
        site seat, and open applications seat."""
        # wrong task
        task1 = Task(
            event=self.ttt_event_non_open,
            person=self.test_person_1,
            role=self.learner,
            seat_membership=self.membership,
            seat_open_training=True,
        )

        with self.assertRaises(ValidationError) as cm:
            task1.full_clean()
        exception = cm.exception
        self.assertNotIn("seat_membership", exception.error_dict)
        self.assertNotIn("seat_open_training", exception.error_dict)

    def test_seats_for_learners_only(self) -> None:
        """Ensure that only learners can be assigned seats."""

        # first wrong task
        task1 = Task(
            event=self.ttt_event_open,
            person=self.test_person_1,
            role=self.instructor,
            seat_membership=self.membership,
            seat_open_training=False,
        )
        # second wrong task
        task2 = Task(
            event=self.ttt_event_open,
            person=self.test_person_2,
            role=self.helper,
            seat_membership=None,
            seat_open_training=True,
        )

        with self.assertRaises(ValidationError) as cm:
            task1.full_clean()
        exception = cm.exception
        self.assertEqual({"role"}, exception.error_dict.keys())

        with self.assertRaises(ValidationError) as cm:
            task2.full_clean()
        exception = cm.exception
        self.assertEqual({"role"}, exception.error_dict.keys())

        # first good task
        task3 = Task(
            event=self.ttt_event_open,
            person=self.test_person_2,
            role=self.learner,
            seat_membership=self.membership,
            seat_open_training=False,
        )
        # second good task
        task4 = Task(
            event=self.ttt_event_open,
            person=self.test_person_2,
            role=self.learner,
            seat_membership=None,
            seat_open_training=True,
        )
        task3.full_clean()
        task4.full_clean()
