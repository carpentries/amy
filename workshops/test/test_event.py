from datetime import datetime, timedelta, date
from urllib.parse import urlencode
import sys

from django.core.urlresolvers import reverse
from django.db.utils import IntegrityError
from ..models import (Event, Host, Tag, Role, Task, Award, Badge, TodoItem)
from ..forms import EventForm, EventsMergeForm
from .base import TestBase


class TestEvent(TestBase):
    "Tests for the event model and its manager."

    def setUp(self):
        self._setUpNonInstructors()
        self._setUpUsersAndLogin()

        # Create a test tag
        Tag.objects.create(name='Test Tag', details='For testing')

        # Create a test role
        Role.objects.create(name='Test Role')

        # Set up generic events.
        self._setUpEvents()

    def test_online_country_enforced_values(self):
        """Ensure that events from 'Online' country (W3) get some location data
        forced upon `save()`."""
        e = Event.objects.create(slug='online-event', country='W3',
                                 host=Host.objects.first())
        self.assertEqual(e.venue, 'Internet')
        self.assertEqual(e.address, 'Internet')
        self.assertAlmostEqual(e.latitude, -48.876667)
        self.assertAlmostEqual(e.longitude, -123.393333)

        e = Event.objects.create(slug='offline-event', country='US',
                                 host=Host.objects.first())
        self.assertNotEqual(e.venue, 'Internet')
        self.assertNotEqual(e.address, 'Internet')
        self.assertIsNone(e.latitude)
        self.assertIsNone(e.longitude)

    def test_get_uninvoiced_events(self):
        """Test that the events manager can find events that owe money"""

        uninvoiced_events = Event.objects.uninvoiced_events()

        # There should be as many as there are strictly future events.
        assert len(uninvoiced_events) == self.num_uninvoiced_events

        # Check that events with a fee of zero or None are still on this list
        assert any([x for x in uninvoiced_events if not x.admin_fee])

    def test_get_upcoming_events(self):
        """Test that the events manager can find upcoming events"""

        upcoming_events = Event.objects.upcoming_events()
        assert len(upcoming_events) == self.num_upcoming
        assert all(['upcoming' in e.slug for e in upcoming_events])

    def test_get_past_events(self):
        """Test that the events manager can find past events"""

        past_events = Event.objects.past_events()

        assert len(past_events) == 9

        # They should all start with past
        assert all(['past' in e.slug for e in past_events])

    def test_get_ongoing_events(self):
        """Test the events manager can find all events overlapping today.

        Include events that (according to the timestamp) are not ongoing,
        but which started or finished today.
        """

        ongoing_events = Event.objects.ongoing_events()
        event_slugs = [e.slug for e in ongoing_events]
        correct_slugs = ['starts_today_ongoing',
                         'ends_tomorrow_ongoing',
                         'ends_today_ongoing', ]

        if sys.version_info >= (3,):
            self.assertCountEqual(event_slugs, correct_slugs)
        else:
            self.assertItemsEqual(event_slugs, correct_slugs)

    def test_unpublished_events(self):
        """Ensure that events manager finds unpublished events correctly."""
        all_events = Event.objects.all()
        self.assertEqual(set(all_events),
                         set(Event.objects.unpublished_events()))
        event_considered_published = Event.objects.create(
            slug='published',
            start=date.today() + timedelta(days=3),
            end=date.today() + timedelta(days=6),
            latitude=-10.0, longitude=10.0,
            country='US', venue='University',
            address='Phenomenal Street',
            url='http://url/',
            host=Host.objects.all().first(),
        )
        self.assertNotIn(event_considered_published,
                         Event.objects.unpublished_events())

    def test_delete_event(self):
        """Make sure deleted event and its tasks are no longer accessible."""
        event = Event.objects.get(slug="starts_today_ongoing")
        role1 = Role.objects.create(name='NonInstructor')
        t1 = Task.objects.create(event=event, person=self.spiderman,
                                 role=role1)
        t2 = Task.objects.create(event=event, person=self.ironman,
                                 role=role1)
        t3 = Task.objects.create(event=event, person=self.blackwidow,
                                 role=role1)
        event.task_set = [t1, t2, t3]
        event.save()

        rv = self.client.get(reverse('event_delete', args=[event.pk, ]))
        assert rv.status_code == 302

        with self.assertRaises(Event.DoesNotExist):
            Event.objects.get(slug="starts_today_ongoing")

        for t in [t1, t2, t3]:
            with self.assertRaises(Task.DoesNotExist):
                Task.objects.get(pk=t.pk)

    def test_delete_event_with_tasks_and_awards(self):
        """Ensure we cannot delete an event with related tasks and awards.

        Deletion is prevented via Award.event's on_delete=PROTECT."""
        event = Event.objects.get(slug="starts_today_ongoing")
        role = Role.objects.create(name='NonInstructor')
        badge = Badge.objects.create(name='noninstructor',
                                     title='Non-instructor',
                                     criteria='')
        task = Task.objects.create(event=event, person=self.spiderman,
                                   role=role)
        award = Award.objects.create(person=self.spiderman,
                                     badge=badge,
                                     awarded=date.today(),
                                     event=event)

        rv = self.client.get(reverse('event_delete', args=[event.pk, ]))
        assert rv.status_code == 200

        content = rv.content.decode('utf-8')
        assert "Failed to delete" in content
        assert "awards" in content

        # make sure these objects were not deleted
        Event.objects.get(pk=event.pk)
        Badge.objects.get(pk=badge.pk)
        Task.objects.get(pk=task.pk)
        Award.objects.get(pk=award.pk)

    def test_repository_website_url(self):
        test_host = Host.objects.all()[0]
        links = [
            'http://user-name.github.com/repo-name',
            'http://user-name.github.io/repo-name',
            'https://user-name.github.com/repo-name',
            'https://user-name.github.io/repo-name',
            'http://user-name.github.com/repo-name/',
            'http://user-name.github.io/repo-name/',
            'https://user-name.github.com/repo-name/',
            'https://user-name.github.io/repo-name/',
            'http://github.com/user-name/repo-name',
            'http://github.com/user-name/repo-name/',
            'https://github.com/user-name/repo-name',
            'https://github.com/user-name/repo-name/',
        ]
        REPO = 'https://github.com/user-name/repo-name'
        WEBSITE = 'https://user-name.github.io/repo-name/'
        for index, link in enumerate(links):
            event = Event.objects.create(
                slug='e{}'.format(index),
                host=test_host,
                url=link
            )
            assert event.repository_url == REPO
            assert event.website_url == WEBSITE

    def test_wrong_repository_website_urls(self):
        test_host = Host.objects.all()[0]
        link = 'http://en.wikipedia.org/'
        event = Event.objects.create(
            slug='test-event',
            host=test_host,
            url=link
        )
        assert event.repository_url == link
        assert event.website_url == link


class TestEventViews(TestBase):
    "Tests for the event views"

    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpNonInstructors()

        self.learner = Role.objects.get_or_create(name='learner')[0]

        # Create a test host
        self.test_host = Host.objects.create(domain='example.com',
                                             fullname='Test Host')

        # Create a test tag
        self.test_tag = Tag.objects.create(name='Test Tag',
                                           details='For testing')

        # Create fifty new events
        for i in range(50):
            event_start = datetime.now()
            Event.objects.create(start=event_start,
                                 slug='test_event_{0}'.format(i),
                                 host=self.test_host,
                                 admin_fee=0)

    def test_events_view_paginated(self):

        events_url = reverse('all_events')
        events_url += '?items_per_page=10'
        response = self.client.get(events_url)

        # We asked for max 10 events, make sure we got them
        view_events = response.context['all_events']

        assert len(view_events) == 10

    def test_can_request_all_events(self):

        events_url = reverse('all_events')
        events_url += '?items_per_page=all'
        response = self.client.get(events_url)

        # We asked for all events, make sure we got them
        view_events = response.context['all_events']
        all_events = list(Event.objects.all())

        if sys.version_info >= (3,):
            self.assertCountEqual(view_events, all_events)
        else:
            self.assertItemsEqual(view_events, all_events)

    def test_invalid_items_per_page_gives_default_pagination(self):

        events_url = reverse('all_events')
        events_url += '?items_per_page=not_an_integer'
        response = self.client.get(events_url)

        # View should be paginated by default, so we shouldn't get all events
        view_events = response.context['all_events']

        assert len(view_events) < 50

    def test_non_integer_page_no_returns_first_page(self):

        events_url = reverse('all_events')
        events_url += '?items_per_page=10&page=not_an_integer'
        response = self.client.get(events_url)

        # Get the events for this page
        view_events = response.context['all_events']

        # They should still be paginated
        assert len(view_events) == 10

        # This should be the first page
        assert view_events.number == 1

    def test_page_no_too_large_returns_last_page(self):

        events_url = reverse('all_events')
        events_url += '?items_per_page=10&page=999'
        response = self.client.get(events_url)

        # Get the events for this page
        view_events = response.context['all_events']

        # They should still be paginated
        assert len(view_events) == 10

        # This should be the first page
        assert view_events.number == 5

    def test_add_minimal_event(self):
        host = Host.objects.get(fullname='Test Host')
        response = self.client.post(
            reverse('event_add'),
            {
                'host': host.id,
                'tags': [self.test_tag.id],
                'administrator': host.id,
            })
        if response.status_code == 302:
            url = response['location']
            event_id = int(url.rsplit('/', 1)[1])
            event = Event.objects.get(id=event_id)
            assert event.host == host, (
                'New event has wrong host: {} != {}'.format(event.host, host))
            tags = list(event.tags.all())
            assert tags == [self.test_tag], (
                'New event has wrong tags: {} != {}'.format(tags,
                                                            [self.test_tag]))
        else:
            self._check_status_code_and_parse(response, 200)
            assert False, 'expected 302 redirect after post'

    def test_add_two_minimal_events(self):
        host = Host.objects.get(fullname='Test Host')
        url = reverse('event_add')
        data = {
                'host': host.id,
                'tags': [self.test_tag.id],
                'administrator': host.id,
            }
        response = self.client.post(url, data)
        assert response.status_code == 302, (
            'expected 302 redirect after first post, got {}'.format(
            response.status_code))
        response = self.client.post(url, data)
        if response.status_code != 302:
            self._check_status_code_and_parse(response, 200)
            assert response.status_code == 302, (
                'expected 302 redirect after second post, got {}'.format(
                    response.status_code))

    def test_unique_slug(self):
        """Ensure events with the same slugs are prohibited.

        This is a regression test for
        https://github.com/swcarpentry/amy/issues/427"""
        Event.objects.create(host=self.test_host, slug='testing-unique-slug')
        with self.assertRaises(IntegrityError):
            Event.objects.create(host=self.test_host,
                                 slug='testing-unique-slug')

    def test_unique_empty_slug(self):
        """Ensure events with no slugs are saved to the DB.

        This is a regression test introduces with one change from
        https://github.com/swcarpentry/amy/issues/427
        (saving empty slug strings to the DB should result in NULL values)."""
        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': '',
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 302

        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 302

    def test_start_date_gte_end_date(self):
        """Ensure event's start date is earlier than it's end date.

        This is a regression test for
        https://github.com/swcarpentry/amy/issues/436"""
        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': 'test-event',
            'start': date(2015, 7, 20),
            'end': date(2015, 7, 19),
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Must not be earlier than start date' in content

        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': 'test-event',
            'start': date(2015, 7, 20),
            'end': date(2015, 7, 20),
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 302

        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': 'test-event2',
            'start': date(2015, 7, 20),
            'end': date(2015, 7, 21),
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 302

    def test_negative_admin_fee_attendance(self):
        """Ensure we disallow negative admin fee or attendance.

        This is a regression test for
        https://github.com/swcarpentry/amy/issues/435."""
        error_str = "Ensure this value is greater than or equal to 0."

        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': 'test-event',
            'admin_fee': -1200,
        }

        f = EventForm(data)
        self.assertIn('admin_fee', f.errors)
        self.assertIn(error_str, f.errors['admin_fee'])

        del data['admin_fee']
        data['attendance'] = -36
        f = EventForm(data)
        self.assertIn('attendance', f.errors)
        self.assertIn(error_str, f.errors['attendance'])

        data['admin_fee'] = 0
        data['attendance'] = 0
        f = EventForm(data)
        self.assertNotIn('admin_fee', f.errors)
        self.assertNotIn('attendance', f.errors)

        data['slug'] = 'test-event2'
        data['admin_fee'] = 1200
        data['attendance'] = 36
        f = EventForm(data)
        self.assertTrue(f.is_valid())

    def test_number_of_attendees_increasing(self):
        """Ensure event.attendance gets bigger after adding new learners."""
        event = Event.objects.get(slug='test_event_0')
        event.attendance = 0  # testing for numeric case
        event.save()

        data = {
            'task-role': self.learner.pk,
            'task-event': event.pk,
            'task-person_1': self.spiderman.pk,
        }
        self.client.post(reverse('event_edit', args=[event.pk]), data)
        event.refresh_from_db()
        assert event.attendance == 1

    def test_slug_against_illegal_characters(self):
        """Regression test: disallow events with slugs with wrong characters.

        Only [\w-] are allowed."""
        data = {
            'slug': '',
            'host_1': Host.objects.all()[0].pk,
            'tags': Tag.objects.all(),
        }
        for slug in ['a/b', 'a b', 'a!b', 'a.b', 'a\\b', 'a?b']:
            with self.subTest(slug=slug):
                data['slug'] = slug
                f = EventForm(data)
                self.assertEqual(f.is_valid(), False)
                self.assertIn('slug', f.errors)

        # allow dashes in the slugs
        data['slug'] = 'a-b'
        f = EventForm(data)
        self.assertEqual(f.is_valid(), False)
        self.assertNotIn('slug', f.errors)

    def test_display_of_event_without_start_date(self):
        """A bug prevented events without start date to throw a 404.

        This is a regression test against that bug.
        The error happened when "".format encountered None instead of
        datetime."""
        event = Event.objects.create(slug='regression_event_0',
                                     host=self.test_host)
        rv = self.client.get(reverse('event_details', args=[event.pk]))
        assert rv.status_code == 200


class TestEventNotes(TestBase):
    """Make sure notes once written are saved forever!"""

    def setUp(self):
        self._setUpUsersAndLogin()

        # a test host is required for all new events
        self.test_host = Host.objects.create(domain='example.com',
                                             fullname='Test Host')

        # prepare a lifespan of all events
        self.event_start = datetime.now() + timedelta(days=-1)
        self.event_end = datetime.now() + timedelta(days=1)

    def test_event_without_notes(self):
        "Make sure event without notes don't have NULLed field ``notes``"
        e = Event(start=self.event_start,
                  end=self.event_end,
                  slug='no_notes',
                  host=self.test_host,
                  admin_fee=100)

        # test for field's default value (the field is not NULL)
        self.assertEqual(e.notes, "")  # therefore the field is not NULL

    def test_event_with_notes(self):
        "Make sure event with notes are correctly stored"

        notes = "This event's going to be extremely exhausting."

        e = Event(start=self.event_start,
                  end=self.event_end,
                  slug='with_notes',
                  host=self.test_host,
                  admin_fee=100,
                  notes=notes)

        # make sure that notes have been saved
        self.assertEqual(e.notes, notes)
