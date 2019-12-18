from itertools import product
from datetime import datetime, timedelta, date

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from autoemails.actions import NewInstructorAction
from autoemails.models import EmailTemplate, Trigger, RQJob
from autoemails.tests.base import FakeRedisTestCaseMixin
from workshops.tests.base import TestBase, SuperuserMixin
from workshops.models import (
    Task,
    Event,
    Role,
    Person,
    Organization,
    Tag,
    Membership,
)
import workshops.views
from workshops.views import TaskCreate, TaskUpdate, TaskDelete


class TestTask(TestBase):
    "Tests for the task model, its manager and views"

    def setUp(self):
        self.fixtures = {}

        self._setUpTags()
        self._setUpRoles()

        test_host = Organization.objects.create(
            domain='example.com', fullname='Test Organization')

        self.test_person_1 = Person.objects.create(
            personal='Test', family='Person1', username="person1")

        self.test_person_2 = Person.objects.create(
            personal='Test', family='Person2', username="person2")

        test_event_1 = Event.objects.create(
            start=datetime.now(), slug='test_event_1', host=test_host,
            admin_fee=0)

        test_event_2 = Event.objects.create(
            start=datetime.now(), slug='test_event_2', host=test_host,
            admin_fee=0)

        test_event_3 = Event.objects.create(
            start=datetime.now(), slug='test_event_3', host=test_host,
            admin_fee=0)

        instructor_role = Role.objects.get(name="instructor")
        self.learner = Role.objects.get(name="learner")
        helper_role = Role.objects.get(name="helper")
        roles = [instructor_role, self.learner, helper_role]
        people = [self.test_person_1, self.test_person_2]

        for role, person in product(roles, people):
            Task.objects.create(person=person, role=role, event=test_event_3)

        test_role_1 = Role.objects.create(name='test_role_1')
        test_role_2 = Role.objects.create(name='test_role_2')

        test_task_1 = Task.objects.create(
            person=self.test_person_1, event=test_event_1, role=test_role_1)

        test_task_2 = Task.objects.create(
            person=self.test_person_2, event=test_event_2, role=test_role_2)

        self.fixtures['test_task_1'] = test_task_1
        self.fixtures['test_task_2'] = test_task_2

        # create 3 events: one without TTT tag, and two with; out of the two,
        # one is allowed to have open applications, the other is not.
        self.non_ttt_event = Event.objects.create(
            start=datetime.now(), slug="non-ttt-event", host=test_host,
        )
        self.non_ttt_event.tags.set(
            Tag.objects.filter(name__in=['SWC', 'DC']))
        self.ttt_event_open = Event.objects.create(
            start=datetime.now(), slug="ttt-event-open-app", host=test_host,
            open_TTT_applications=True,
        )
        self.ttt_event_open.tags.set(
            Tag.objects.filter(name__in=['DC', 'TTT']))
        self.ttt_event_non_open = Event.objects.create(
            start=datetime.now(), slug="ttt-event-closed-app", host=test_host,
            open_TTT_applications=False,
        )
        self.ttt_event_non_open.tags.set(
            Tag.objects.filter(name__in=['DC', 'TTT']))

        # create a membership
        self.membership = Membership.objects.create(
            variant='partner',
            agreement_start=datetime.now() - timedelta(weeks=4),
            agreement_end=datetime.now() + timedelta(weeks=4),
            contribution_type='financial',
            organization=test_host,
        )

        self._setUpUsersAndLogin()

    def test_task_detail_view_reachable_from_event_person_and_role_of_task(self):

        correct_task = self.fixtures['test_task_1']
        response = self.client.get(reverse('task_details', args=[str(correct_task.id)]))
        assert response.context['task'].pk == correct_task.pk

    def test_add_task_with_correct_url(self):
        '''Ensure that task can be saved with correct URL field'''
        task = self.fixtures['test_task_1']
        payload = {
            'event': task.event.pk,
            'person': task.person.pk,
            'role': task.role.pk,
            'title': 'Task title',
            'url': 'http://example.org',
        }
        response = self.client.post(
            reverse('task_edit', kwargs={'task_id':task.pk}),
            payload,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('task_details', kwargs={'task_id':task.pk})
        )
        task.refresh_from_db()
        self.assertEqual(task.url, 'http://example.org')
        self.assertEqual(response.context['task'].url, 'http://example.org')

    def test_add_task_with_incorrect_url(self):
        '''Ensure that a task object cannot be saved with incorrect URL field'''
        task = self.fixtures['test_task_1']
        payload = {
            'event': task.event.pk,
            'person': task.person.pk,
            'role': task.role.pk,
            'title': 'Task title',
            'url': 'htp://example.org',
        }
        response = self.client.post(
            reverse('task_edit', kwargs={'task_id':task.pk}),
            payload,
        )
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.url, '')

    def test_add_duplicate_task(self):
        '''Ensure that duplicate tasks with empty url field cannot exist'''
        task_1 = self.fixtures['test_task_1']
        with self.assertRaises(IntegrityError):
            Task.objects.create(
                event=task_1.event,
                person=task_1.person,
                role=task_1.role,
            )

    def test_add_duplicate_task_with_url(self):
        '''Ensure that duplicate tasks cannot exist'''
        task_1 = self.fixtures['test_task_1']
        task_1.url = 'http://example.org'
        task_1.save()
        with self.assertRaises(IntegrityError):
            Task.objects.create(
                event=task_1.event,
                person=task_1.person,
                role=task_1.role,
                url=task_1.url,
            )

    def test_task_edit_view_reachable_from_event_person_and_role_of_task(self):
        correct_task = self.fixtures['test_task_1']
        url_kwargs = {'task_id': correct_task.id}
        response = self.client.get(reverse('task_edit',
                                   kwargs=url_kwargs))
        assert response.context['task'].pk == correct_task.pk

    def test_task_manager_roles_lookup(self):
        """Test TaskManager methods for looking up roles by names."""
        event = Event.objects.get(slug='test_event_3')
        instructors = event.task_set.instructors()
        learners = event.task_set.learners()
        helpers = event.task_set.helpers()
        tasks = event.task_set.all()

        assert set(tasks) == set(instructors) | set(learners) | set(helpers)

    def test_delete_task(self):
        """Make sure deleted task is longer accessible."""
        for task in Task.objects.all():
            rv = self.client.post(reverse('task_delete', args=[task.pk, ]))
            assert rv.status_code == 302

            with self.assertRaises(Task.DoesNotExist):
                Task.objects.get(pk=task.pk)

    def test_seats_validation(self):
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
        self.assertIn('seat_membership', exception.error_dict)
        self.assertNotIn('seat_open_training', exception.error_dict)

        with self.assertRaises(ValidationError) as cm:
            task2.full_clean()
        exception = cm.exception
        self.assertIn('seat_open_training', exception.error_dict)
        self.assertNotIn('seat_membership', exception.error_dict)

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

    def test_open_applications_TTT(self):
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
        self.assertIn('seat_open_training', exception.error_dict)
        self.assertNotIn('seat_membership', exception.error_dict)

        task2.full_clean()

    def test_both_open_app_and_seat(self):
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
        self.assertNotIn('seat_membership', exception.error_dict)
        self.assertNotIn('seat_open_training', exception.error_dict)


class TestTaskCreateAutoEmails(FakeRedisTestCaseMixin, SuperuserMixin,
                               TestCase):
    def setUp(self):
        super().setUp()

        # save scheduler and connection data
        self._saved_scheduler = workshops.views.scheduler
        self._saved_redis_connection = workshops.views.redis_connection
        # overwrite them
        workshops.views.scheduler = self.scheduler
        workshops.views.redis_connection = self.connection

    def tearDown(self):
        super().tearDown()
        workshops.views.scheduler = self._saved_scheduler
        workshops.views.redis_connection = self._saved_redis_connection

    def _prepare_data(self):
        Tag.objects.bulk_create([
            Tag(name='SWC'),
            Tag(name='DC'),
            Tag(name='LC'),
        ])

        Role.objects.create(name='instructor')

        self.test_host = Organization.objects.create(
            domain='example.com', fullname='Test Organization')

        self.test_person_1 = Person.objects.create(
            personal='Test', family='Person1', username="person1")

        self.test_event_1 = Event.objects.create(
            slug='test-event',
            host=Organization.objects.first(),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country='GB',
            venue='Ministry of Magic',
            address='Underground',
            latitude=20.0,
            longitude=20.0,
            url='https://test-event.example.com',
        )
        self.test_event_1.tags.set(
            Tag.objects.filter(name__in=['SWC', 'DC', 'LC']))

        template = EmailTemplate.objects.create(
            slug='sample-template',
            subject='Welcome!',
            to_header='',
            from_header='test@address.com',
            cc_header='copy@example.org',
            bcc_header='bcc@example.org',
            reply_to_header='',
            html_template='<h1>Welcome</h1>',
            text_template='*Welcome*',
        )
        trigger = Trigger.objects.create(action='new-instructor',
                                         template=template)

    def test_methods_implemented(self):
        view = TaskCreate()
        view.get_logger()
        view.get_scheduler()
        view.get_redis_connection()
        view.get_triggers()
        # unnecessary for a view that only uses `action_add`
        # view.get_jobs()
        try:
            view.objects()
        except AttributeError:
            # it's fine
            pass

    def test_job_scheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        role = Role.objects.get(name='instructor')

        # no tasks
        self.assertFalse(Task.objects.all())
        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        self.client.force_login(self.admin)
        data = {
            'event': self.test_event_1.pk,
            'person': self.test_person_1.pk,
            'role': role.pk,
        }
        response = self.client.post(reverse('task_add'), data, follow=True)
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        self.assertIn("New email was scheduled",
                      response.content.decode('utf-8'))

        # new task appeared
        self.assertEqual(Task.objects.count(), 1)

        # ensure the new task passes action checks
        task = Task.objects.first()
        self.assertTrue(NewInstructorAction.check(task))

        # 1 new jobs
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjobs
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)


class TestTaskUpdateAutoEmails(FakeRedisTestCaseMixin, SuperuserMixin,
                               TestCase):
    def setUp(self):
        super().setUp()

        # save scheduler and connection data
        self._saved_scheduler = workshops.views.scheduler
        self._saved_redis_connection = workshops.views.redis_connection
        # overwrite them
        workshops.views.scheduler = self.scheduler
        workshops.views.redis_connection = self.connection

    def tearDown(self):
        super().tearDown()
        workshops.views.scheduler = self._saved_scheduler
        workshops.views.redis_connection = self._saved_redis_connection

    def _prepare_data(self):
        Tag.objects.bulk_create([
            Tag(name='SWC'),
            Tag(name='DC'),
            Tag(name='LC'),
        ])

        self.instructor = Role.objects.create(name='instructor')
        self.helper = Role.objects.create(name='helper')

        self.host = Organization.objects.create(
            domain='example.com', fullname='Test Organization')

        self.person_1 = Person.objects.create(
            personal='Test', family='Person1', username="person1")

        self.event_1 = Event.objects.create(
            slug='test-event',
            host=self.host,
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country='GB',
            venue='Ministry of Magic',
            address='Underground',
            latitude=20.0,
            longitude=20.0,
            url='https://test-event.example.com',
        )
        self.event_1.tags.set(
            Tag.objects.filter(name__in=['SWC', 'DC', 'LC']))

        template = EmailTemplate.objects.create(
            slug='sample-template',
            subject='Welcome!',
            to_header='',
            from_header='test@address.com',
            cc_header='copy@example.org',
            bcc_header='bcc@example.org',
            reply_to_header='',
            html_template='<h1>Welcome</h1>',
            text_template='*Welcome*',
        )
        trigger = Trigger.objects.create(action='new-instructor',
                                         template=template)

    def test_methods_implemented(self):
        view = TaskUpdate()
        view.get_logger()
        view.get_scheduler()
        view.get_redis_connection()
        view.get_triggers()
        # it's fine
        with self.assertRaises(AttributeError):
            view.get_jobs()
        # it's fine
        with self.assertRaises(AttributeError):
            view.objects()

    def test_job_scheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # this task shouldn't trigger action
        task = Task.objects.create(
            role=self.helper,
            person=self.person_1,
            event=self.event_1,
        )
        self.assertFalse(NewInstructorAction.check(task))

        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        # change task's role to instructor and save
        self.client.force_login(self.admin)
        data = {
            'event': self.event_1.pk,
            'person': self.person_1.pk,
            'role': self.instructor.pk
        }
        response = self.client.post(reverse('task_edit', args=[task.pk]), data,
                                    follow=True)
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        self.assertIn("New email was scheduled",
                      response.content.decode('utf-8'))

        task.refresh_from_db()
        self.assertTrue(NewInstructorAction.check(task))

        # 1 new job
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjob
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

    def test_job_unscheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # this task won't trigger an action if we created it via a view
        task = Task.objects.create(
            role=self.helper,
            person=self.person_1,
            event=self.event_1,
        )
        self.assertFalse(NewInstructorAction.check(task))
        # no jobs - again, due to not creating via WWW
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs - again, due to not creating via WWW
        self.assertFalse(RQJob.objects.all())

        # change task's role to instructor and save
        self.client.force_login(self.admin)
        data = {
            'role': self.instructor.pk,
            'person': self.person_1.pk,
            'event': self.event_1.pk,
        }
        response = self.client.post(reverse('task_edit', args=[task.pk]), data,
                                    follow=True)
        self.assertContains(response, 'New email was scheduled')
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure now we have the job
        task.refresh_from_db()
        self.assertTrue(NewInstructorAction.check(task))

        # 1 new job
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjob
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

        # now change the task back to helper
        data = {
            'event': self.event_1.pk,
            'person': self.person_1.pk,
            'role': self.helper.pk
        }
        response = self.client.post(reverse('task_edit', args=[task.pk]), data,
                                    follow=True)
        self.assertContains(response, 'Scheduled email was removed')
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure the task doesn't pass checks anymore
        task.refresh_from_db()
        self.assertFalse(NewInstructorAction.check(task))

        # no job
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjob
        self.assertEqual(RQJob.objects.count(), 0)


class TestTaskDeleteAutoEmails(FakeRedisTestCaseMixin, SuperuserMixin,
                               TestCase):
    def setUp(self):
        super().setUp()

        # save scheduler and connection data
        self._saved_scheduler = workshops.views.scheduler
        self._saved_redis_connection = workshops.views.redis_connection
        # overwrite them
        workshops.views.scheduler = self.scheduler
        workshops.views.redis_connection = self.connection

    def tearDown(self):
        super().tearDown()
        workshops.views.scheduler = self._saved_scheduler
        workshops.views.redis_connection = self._saved_redis_connection

    def _prepare_data(self):
        Tag.objects.bulk_create([
            Tag(name='SWC'),
            Tag(name='DC'),
            Tag(name='LC'),
        ])

        self.instructor = Role.objects.create(name='instructor')
        self.helper = Role.objects.create(name='helper')

        self.host = Organization.objects.create(
            domain='example.com', fullname='Test Organization')

        self.person_1 = Person.objects.create(
            personal='Test', family='Person1', username="person1")

        self.event_1 = Event.objects.create(
            slug='test-event',
            host=self.host,
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
            country='GB',
            venue='Ministry of Magic',
            address='Underground',
            latitude=20.0,
            longitude=20.0,
            url='https://test-event.example.com',
        )
        self.event_1.tags.set(
            Tag.objects.filter(name__in=['SWC', 'DC', 'LC']))

        template = EmailTemplate.objects.create(
            slug='sample-template',
            subject='Welcome!',
            to_header='',
            from_header='test@address.com',
            cc_header='copy@example.org',
            bcc_header='bcc@example.org',
            reply_to_header='',
            html_template='<h1>Welcome</h1>',
            text_template='*Welcome*',
        )
        trigger = Trigger.objects.create(action='new-instructor',
                                         template=template)

    def test_methods_implemented(self):
        view = TaskDelete()
        view.get_logger()
        view.get_scheduler()
        view.get_redis_connection()
        # unnecessary for a view that only uses `action_remove`
        # view.get_triggers()

        # it's fine
        with self.assertRaises(AttributeError):
            view.get_jobs()
        # it's fine
        with self.assertRaises(AttributeError):
            view.objects()

    def test_job_unscheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        self.client.force_login(self.admin)
        data = {
            'event': self.event_1.pk,
            'person': self.person_1.pk,
            'role': self.instructor.pk,
        }
        response = self.client.post(reverse('task_add'), data, follow=True)
        self.assertContains(response, "New email was scheduled")
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # new task appeared
        self.assertEqual(Task.objects.count(), 1)

        # ensure the new task passes action checks
        task = Task.objects.first()
        self.assertTrue(NewInstructorAction.check(task))

        # 1 new jobs
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjobs
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

        # now remove the task
        response = self.client.post(reverse('task_delete', args=[task.pk]),
                                    follow=True)
        self.assertContains(response, 'Scheduled email was removed')
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # task is gone
        with self.assertRaises(Task.DoesNotExist):
            task.refresh_from_db()

        # no job
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjob
        self.assertEqual(RQJob.objects.count(), 0)
