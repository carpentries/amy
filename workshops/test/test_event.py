from datetime import datetime, timedelta, date
import sys
import cgi

from django.test import TestCase
from django.core.urlresolvers import reverse
from ..models import (Event, Host, Tag, Person, Role, Task, Award, Badge)
from .base import TestBase


class TestEvent(TestBase):
    "Tests for the event model and its manager."

    def setUp(self):
        self._setUpNonInstructors()
        self._setUpUsersAndLogin()

        # Create a test tag
        test_tag = Tag.objects.create(name='Test Tag', details='For testing')

        # Create a test role
        test_role = Role.objects.create(name='Test Role')

        # Set up generic events.
        self._setUpEvents()

    def test_get_uninvoiced_events(self):
        """Test that the events manager can find events that owe money"""

        uninvoiced_events = Event.objects.uninvoiced_events()

        # There should be as many as there are strictly future events.
        assert len(uninvoiced_events) == self.num_uninvoiced_events

        # Check that events with a fee of zero are not in the list of uninvoiced events.
        assert not any([x for x in uninvoiced_events if x.admin_fee == 0])

    def test_get_future_events(self):
        """Test that the events manager can find upcoming events"""

        upcoming_events = Event.objects.upcoming_events()
        assert len(upcoming_events) == self.num_upcoming
        assert all(['upcoming' in e.slug for e in upcoming_events])

    def test_get_past_events(self):
        """Test that the events manager can find past events"""

        past_events = Event.objects.past_events()

        # There are 3 past events
        assert len(past_events) == 8

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

    def test_edit_event(self):
        """ Test that an event can be edited, and that people can be
            added from the event edit page.
        """

        event = Event.objects.all()[0]
        tag = Tag.objects.get(name='Test Tag')
        role = Role.objects.get(name='Test Role')
        url, values = self._get_initial_form_index(0, 'event_edit', event.id)
        assert len(values) > 0
        values['event-end'] = ''
        values['event-tags'] = tag.id
        assert "event-reg_key" in values, \
            'No reg key in initial form'
        new_reg_key = 'test_reg_key'
        assert event.reg_key != new_reg_key, \
            'Would be unable to tell if reg_key had changed'
        values['event-reg_key'] = new_reg_key
        response = self.client.post(url, values, follow=True)
        content = response.content.decode('utf-8')
        assert new_reg_key in content

        url, values = self._get_initial_form_index(1, 'event_edit', event.id)
        assert "task-person_0" in values, \
            'No person select in initial form'

        person = Person.objects.all()[0]
        values['task-person_1'] = person.id
        values['task-role'] = role.id

        response = self.client.post(url, values, follow=True)
        content = response.content.decode('utf-8')
        assert "/workshops/person/1" in content
        assert "Test Role" in content

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
        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': 'testing-unique-slug',
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 302

        response = self.client.post(reverse('event_add'), data)
        with self.assertRaises(AssertionError):
            self._check_status_code_and_parse(response, 200)

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
        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': 'test-event',
            'admin_fee': -1200,
        }
        S = "Ensure this value is greater than or equal to 0"
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert content.count(S) == 1

        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': 'test-event',
            'admin_fee': -1200,
            'attendance': -36,
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert content.count(S) == 2

        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': 'test-event',
            'attendance': -36,
        }
        S = "Ensure this value is greater than or equal to 0"
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert content.count(S) == 1

        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': 'test-event',
            'admin_fee': 0,
            'attendance': 0,
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 302

        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': 'test-event2',
            'admin_fee': 1200,
            'attendance': 36,
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 302


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
