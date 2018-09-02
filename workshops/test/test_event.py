from datetime import datetime, timedelta, date
from urllib.parse import urlencode
import sys

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.utils import IntegrityError
from django.urls import reverse

from ..management.commands.check_for_workshop_websites_updates import (
    Command as WebsiteUpdatesCommand)
from ..models import (Event, Organization, Tag, Role, Task, Award, Badge,
                      TodoItem)
from ..forms import EventForm, EventsMergeForm
from .base import TestBase


class TestEvent(TestBase):
    "Tests for the event model and its manager."

    def setUp(self):
        self._setUpAirports()
        self._setUpNonInstructors()
        self._setUpUsersAndLogin()
        self._setUpOrganizations()
        self._setUpRoles()
        self._setUpTags()

        self.TTT_tag = Tag.objects.get(name='TTT')
        self.learner_role = Role.objects.get(name='learner')

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
                                 host=Organization.objects.first())
        self.assertEqual(e.venue, 'Internet')
        self.assertEqual(e.address, 'Internet')
        self.assertAlmostEqual(e.latitude, -48.876667)
        self.assertAlmostEqual(e.longitude, -123.393333)

        e = Event.objects.create(slug='offline-event', country='US',
                                 host=Organization.objects.first())
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
        expected = Event.objects.filter(slug__endswith='upcoming')
        self.assertEqual(set(upcoming_events), set(expected))

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
        correct_slugs = ['ends-tomorrow-ongoing', 'ends-today-ongoing']

        self.assertCountEqual(event_slugs, correct_slugs)

    def test_unpublished_events(self):
        """Ensure that events manager finds unpublished events correctly."""
        expected = Event.objects.exclude(slug__endswith='upcoming') \
                                .exclude(slug__in=['ends-today-ongoing',
                                                   'ends-tomorrow-ongoing']) \
                                .exclude(slug__endswith='cancelled')
        self.assertEqual(set(Event.objects.unpublished_events()),
                         set(expected))

        event_considered_published = Event.objects.create(
            slug='published',
            start=date.today() + timedelta(days=3),
            end=date.today() + timedelta(days=6),
            latitude=-10.0, longitude=10.0,
            country='US', venue='University',
            address='Phenomenal Street',
            url='http://url/',
            host=Organization.objects.all().first(),
        )
        self.assertNotIn(event_considered_published,
                         Event.objects.unpublished_events())

    def test_unpublished_events_displayed_once(self):
        """Regression test: unpublished events can't be displayed more than
        once on the dashboard.  Refer to #977."""
        unpublished_event = Event.objects.create(
            slug='2016-10-20-unpublished',
            start=date(2016, 10, 20),
            end=date(2016, 10, 21),
            host=Organization.objects.first(),
            administrator=Organization.objects.first(),
        )
        unpublished_event.tags.set(Tag.objects.filter(name__in=['TTT', 'online']))

        unpublished = Event.objects.unpublished_events().select_related('host')
        self.assertIn(unpublished_event, unpublished)
        self.assertEqual(
            1, len(unpublished.filter(slug='2016-10-20-unpublished'))
        )

    def test_cancelled_events(self):
        """Regression test: make sure that cancelled events don't show up in
        the unpublished, published or uninvoiced events."""
        cancelled_event = Event.objects.create(
            slug='2017-01-07-cancelled',
            start=date(2017, 1, 7),
            end=date(2017, 1, 8),
            host=Organization.objects.first(),
            administrator=Organization.objects.first(),
        )
        cancelled_event.tags.set(Tag.objects.filter(name='cancelled'))

        published = Event.objects.published_events().select_related('host')
        uninvoiced = Event.objects.uninvoiced_events().select_related('host')
        unpublished = Event.objects.unpublished_events().select_related('host')
        self.assertNotIn(cancelled_event, uninvoiced)
        self.assertNotIn(cancelled_event, published)
        self.assertNotIn(cancelled_event, unpublished)

    def test_delete_event(self):
        """Make sure deleted event without any tasks is no longer accessible."""
        event = Event.objects.get(slug="starts-today-ongoing")

        rv = self.client.post(reverse('event_delete', args=[event.slug]))
        self.assertEqual(rv.status_code, 302)

        with self.assertRaises(Event.DoesNotExist):
            Event.objects.get(slug="starts-today-ongoing")

    def test_delete_event_with_tasks_and_awards(self):
        """Ensure we cannot delete an event with related tasks and awards.

        Deletion is prevented via Award.event's on_delete=PROTECT
        and Task.event's on_delete=PROTECT."""
        event = Event.objects.get(slug="starts-today-ongoing")
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

        rv = self.client.post(reverse('event_delete', args=[event.slug, ]))
        self.assertEqual(rv.status_code, 200)

        content = rv.content.decode('utf-8')
        self.assertIn("Failed to delete", content)
        self.assertIn("tasks", content)
        # not available since it's not propagated by Django
        # to ProtectedError.protected_objects
        #self.assertIn("awards", content)

        # make sure these objects were not deleted
        Event.objects.get(pk=event.pk)
        Badge.objects.get(pk=badge.pk)
        Task.objects.get(pk=task.pk)
        Award.objects.get(pk=award.pk)

    def test_repository_website_url(self):
        test_host = Organization.objects.all()[0]
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
        test_host = Organization.objects.all()[0]
        link = 'http://en.wikipedia.org/'
        event = Event.objects.create(
            slug='test-event',
            host=test_host,
            url=link
        )
        assert event.repository_url == link
        assert event.website_url == link

    def test_open_TTT_applications_validation(self):
        event = Event.objects.create(
            slug='test-event',
            host=self.org_alpha,
        )

        # without TTT tag, the validation fails
        event.open_TTT_applications = True
        with self.assertRaises(ValidationError) as cm:
            event.full_clean()
        exc = cm.exception
        self.assertIn('open_TTT_applications', exc.error_dict)

        # now the validation should pass
        event.tags.set([self.TTT_tag])
        event.full_clean()


class TestEventManager(TestBase):
    def test_ttt(self):
        org = Organization.objects.create(domain='example.com',
                                          fullname='Test Organization')
        ttt_tag = Tag.objects.create(name='TTT')
        first = Event.objects.create(slug='first', host=org)
        second = Event.objects.create(slug='second', host=org)
        second.tags.add(ttt_tag)
        third = Event.objects.create(slug='third', host=org)
        third.tags.add(ttt_tag)

        got = set(Event.objects.ttt())
        expected = {second, third}
        self.assertEqual(got, expected)


class TestEventViews(TestBase):
    "Tests for the event views"

    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpAirports()
        self._setUpNonInstructors()
        self._setUpOrganizations()
        self._setUpTags()

        self.learner = Role.objects.get_or_create(name='learner')[0]

        # Create a test host
        self.test_host = Organization.objects.create(
            domain='example.com', fullname='Test Organization')

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
        host = Organization.objects.get(fullname='Test Organization')
        response = self.client.post(
            reverse('event_add'),
            {
                'slug': '2012-12-21-event-final',
                'host': host.id,
                'tags': [self.test_tag.id],
                'administrator': host.id,
                'invoice_status': 'unknown',
            })
        if response.status_code == 302:
            url = response['location']
            event_slug = url.rstrip('/').rsplit('/', 1)[1]
            event = Event.objects.get(slug=event_slug)
            assert event.host == host, (
                'New event has wrong host: {} != {}'.format(event.host, host))
            tags = list(event.tags.all())
            assert tags == [self.test_tag], (
                'New event has wrong tags: {} != {}'.format(tags,
                                                            [self.test_tag]))
        else:
            self._check_status_code_and_parse(response, 200)
            assert False, 'expected 302 redirect after post'

    def test_unique_slug(self):
        """Ensure events with the same slugs are prohibited.

        This is a regression test for
        https://github.com/swcarpentry/amy/issues/427"""
        Event.objects.create(host=self.test_host, slug='testing-unique-slug')
        with self.assertRaises(IntegrityError):
            Event.objects.create(host=self.test_host,
                                 slug='testing-unique-slug')

    def test_assign_to_field_populated(self):
        """Ensure that we can assign an admin to an event
        from the `event_add` view."""
        data = {
            'slug': '2016-07-09-test',
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'assigned_to': self.admin.pk,
            'invoice_status': 'unknown',
        }
        response = self.client.post(reverse('event_add'), data, follow=True)
        event = Event.objects.get(slug='2016-07-09-test')
        self.assertRedirects(
            response,
            reverse('event_details', kwargs={'slug': event.slug}),
        )
        self.assertEqual(event.assigned_to, self.admin)

    def test_unique_non_empty_slug(self):
        """Ensure events with no slugs are *not* saved to the DB.
        """
        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': '',
            'invoice_status': 'unknown',
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 200

    def test_start_date_gte_end_date(self):
        """Ensure event's start date is earlier than it's end date.

        This is a regression test for
        https://github.com/swcarpentry/amy/issues/436"""
        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': '2016-06-30-test-event',
            'start': date(2015, 7, 20),
            'end': date(2015, 7, 19),
            'invoice_status': 'unknown',
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert 'Must not be earlier than start date' in content

        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': '2016-06-30-test-event',
            'start': date(2015, 7, 20),
            'end': date(2015, 7, 20),
            'invoice_status': 'unknown',
        }
        response = self.client.post(reverse('event_add'), data)
        assert response.status_code == 302

        data = {
            'host': self.test_host.id,
            'tags': [self.test_tag.id],
            'slug': '2016-06-30-test-event2',
            'start': date(2015, 7, 20),
            'end': date(2015, 7, 21),
            'invoice_status': 'unknown',
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
            'slug': '2016-06-30-test-event',
            'admin_fee': -1200,
            'invoice_status': 'unknown',
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

        data['slug'] = '2016-06-30-test-event2'
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
            'role': self.learner.pk,
            'event': event.pk,
            'person': self.spiderman.pk,
        }
        self.client.post(reverse('task_add'), data)
        event.refresh_from_db()
        self.assertEqual(event.attendance, 1)

    def test_slug_illegal_characters(self):
        """Disallow slugs with wrong characters.

        Slug allows only: latin characters, numbers, dashes and underscores.
        Slug format should follow: YYYY-MM-DD-location, where YYYY, MM, DD can
        be unspecified (== 'xx')."""
        data = {
            'slug': '',
            'host': Organization.objects.all()[0].pk,
            'tags': Tag.objects.all(),
            'invoice_status': 'unknown',
        }

        # disallow illegal characters
        for slug_suffix in ['a/b', 'a b', 'a!b', 'a.b', 'a\\b', 'a?b', 'aób']:
            with self.subTest(slug_suffix=slug_suffix):
                data['slug'] = '2016-06-30-{}'.format(slug_suffix)
                f = EventForm(data)
                self.assertEqual(f.is_valid(), False)
                self.assertIn('slug', f.errors)

    def test_slug_illegal_formats(self):
        """Disallow slugs with wrong formats.

        Slug format should follow: YYYY-MM-DD-location, where YYYY, MM, DD can
        be unspecified (== 'xx')."""
        data = {
            'slug': '',
            'host': Organization.objects.all()[0].pk,
            'tags': [Tag.objects.first().pk],
            'invoice_status': 'unknown',
        }

        # disallow invalid formats
        formats = [
            '20166-06-30-Krakow',
            '2016-006-30-Krakow',
            '2016-06-300-Krakow',
            '201-06-30-Krakow',
            '2016-6-30-Krakow',
            '2016-06-3-Krakow',
            'SWC-2016-06-300-Krakow',
            '',
            'xxxxx-xx-xx-Krakow',
            'xxxx-xxx-xx-Krakow',
            'xxxx-xx-xxx-Krakow',
            'xxx-xx-xx-Krakow',
            'xxxx-x-xx-Krakow',
            'xxxx-xx-x-Krakow',
        ]
        for slug in formats:
            with self.subTest(slug=slug):
                data['slug'] = slug
                f = EventForm(data)
                self.assertEqual(f.is_valid(), False)
                self.assertIn('slug', f.errors)

    def test_slug_valid_formats(self):
        """Allow slugs with wrong formats.

        Slug format should follow: YYYY-MM-DD-location, where YYYY, MM, DD can
        be unspecified (== 'xx')."""
        data = {
            'slug': '',
            'host': Organization.objects.all()[0].pk,
            'tags': [Tag.objects.first().pk],
            'invoice_status': 'unknown',
        }

        # allow correct formats
        formats = [
            '2016-06-30-Krakow',
            '2016-06-xx-Krakow',
            '2016-xx-30-Krakow',
            'xxxx-06-30-Krakow',
            '2016-xx-xx-Krakow',
            'xxxx-06-xx-Krakow',
            'xxxx-xx-30-Krakow',
            'xxxx-xx-xx-Krakow',
            '2016-06-30-Krakow-multiple-words',
            '2016-06-xx-Krakow-multiple-words',
            '2016-xx-30-Krakow-multiple-words',
            'xxxx-06-30-Krakow-multiple-words',
            '2016-xx-xx-Krakow-multiple-words',
            'xxxx-06-xx-Krakow-multiple-words',
            'xxxx-xx-30-Krakow-multiple-words',
            'xxxx-xx-xx-Krakow-multiple-words',
        ]
        for slug in formats:
            with self.subTest(slug=slug):
                data['slug'] = slug
                f = EventForm(data)
                self.assertEqual(f.is_valid(), True)
                self.assertNotIn('slug', f.errors)

    def test_display_of_event_without_start_date(self):
        """A bug prevented events without start date to throw a 404.

        This is a regression test against that bug.
        The error happened when "".format encountered None instead of
        datetime."""
        event = Event.objects.create(slug='regression_event_0',
                                     host=self.test_host)
        rv = self.client.get(reverse('event_details', args=[event.slug]))
        assert rv.status_code == 200

    def test_open_TTT_applications_form_validation(self):
        """Ensure validation of `open_TTT_applications` field."""
        data = {
            'slug': '2018-09-02-open-applications',
            'host': self.org_alpha.pk,
            'tags': [Tag.objects.get(name='SWC').pk],
            'invoice_status': 'unknown',
            'open_TTT_applications': True,
        }
        form = EventForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn('open_TTT_applications', form.errors.keys())

        data['tags'] = [Tag.objects.get(name='TTT').pk]
        form = EventForm(data)
        self.assertTrue(form.is_valid())


class TestEventNotes(TestBase):
    """Make sure notes once written are saved forever!"""

    def setUp(self):
        self._setUpUsersAndLogin()

        # a test host is required for all new events
        self.test_host = Organization.objects.create(domain='example.com',
                                             fullname='Test Organization')

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


class TestEventMerging(TestBase):
    def setUp(self):
        self._setUpOrganizations()
        self._setUpAirports()
        self._setUpBadges()
        self._setUpLessons()
        self._setUpRoles()
        self._setUpInstructors()
        self._setUpUsersAndLogin()
        self._setUpTags()
        self._setUpLanguages()

        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Add full-blown events so that we can test merging of everything.
        # Random data such as contact, venue, address, lat/long, URLs or notes
        # were generated with faker (see `fake_database.py` for details).
        self.event_a = Event.objects.create(
            slug='event-a', completed=True, assigned_to=self.harry,
            start=today, end=tomorrow,
            host=self.org_alpha, administrator=self.org_alpha,
            url='http://reichel.com/event-a', language=self.french,
            reg_key='123456',
            admin_fee=2500, invoice_status='not-invoiced',
            attendance=30, contact='moore.buna@schuppe.info', country='US',
            venue='Modi', address='876 Dot Fork',
            latitude=59.987509, longitude=-51.507076,
            learners_pre='http://reichel.com/learners_pre',
            learners_post='http://reichel.com/learners_post',
            instructors_pre='http://reichel.com/instructors_pre',
            instructors_post='http://reichel.com/instructors_post',
            learners_longterm='http://reichel.com/learners_longterm',
            notes='Voluptates hic aspernatur non aut.'
        )
        self.event_a.tags.set(Tag.objects.filter(name__in=['LC', 'DC']))
        self.event_a.task_set.create(person=self.harry,
                                     role=Role.objects.get(name='instructor'))
        self.event_a.todoitem_set.create(completed=False,
                                         title='Find instructors', due=today)

        self.event_b = Event.objects.create(
            slug='event-b', completed=False, assigned_to=self.hermione,
            start=today, end=tomorrow + timedelta(days=1),
            host=self.org_beta, administrator=self.org_beta,
            url='http://www.cummings.biz/event-b', language=self.english,
            reg_key='654321',
            admin_fee=2500, invoice_status='not-invoiced',
            attendance=40, contact='haleigh.schneider@hotmail.com',
            country='GB', venue='Nisi', address='59747 Fernanda Cape',
            latitude=-29.545137, longitude=32.417491,
            learners_pre='http://www.cummings.biz/learners_pre',
            learners_post='http://www.cummings.biz/learners_post',
            instructors_pre='http://www.cummings.biz/instructors_pre',
            instructors_post='http://www.cummings.biz/instructors_post',
            learners_longterm='http://www.cummings.biz/learners_longterm',
            notes='Est qui iusto sapiente possimus consectetur rerum et.'
        )
        self.event_b.tags.set(Tag.objects.filter(name='SWC'))
        # no tasks for this event
        self.event_b.todoitem_set.create(completed=True, title='Test merging',
                                         due=today)

        # some "random" strategy for testing
        self.strategy = {
            'event_a': self.event_a.pk,
            'event_b': self.event_b.pk,
            'id': 'obj_b',
            'slug': 'obj_a',
            'completed': 'obj_b',
            'assigned_to': 'obj_a',
            'start': 'obj_b',
            'end': 'obj_a',
            'host': 'obj_b',
            'administrator': 'obj_a',
            'url': 'obj_b',
            'language': 'obj_b',
            'reg_key': 'obj_a',
            'admin_fee': 'obj_b',
            'invoice_status': 'obj_a',
            'attendance': 'obj_b',
            'country': 'obj_a',
            'latitude': 'obj_b',
            'longitude': 'obj_a',
            'learners_pre': 'obj_b',
            'learners_post': 'obj_a',
            'instructors_pre': 'obj_b',
            'instructors_post': 'obj_a',
            'learners_longterm': 'obj_b',
            'contact': 'obj_a',
            'venue': 'obj_b',
            'address': 'combine',
            'notes': 'obj_a',
            'tags': 'combine',
            'task_set': 'obj_b',
            'todoitem_set': 'obj_a',
        }
        base_url = reverse('events_merge')
        query = urlencode({
            'event_a': self.event_a.pk,
            'event_b': self.event_b.pk
        })
        self.url = '{}?{}'.format(base_url, query)

    def test_form_invalid_values(self):
        """Make sure only a few fields accept third option ("combine")."""
        hidden = {
            'event_a': self.event_a.pk,
            'event_b': self.event_b.pk,
        }
        # fields accepting only 2 options: "obj_a" and "obj_b"
        failing = {
            'id': 'combine',
            'slug': 'combine',
            'completed': 'combine',
            'assigned_to': 'combine',
            'start': 'combine',
            'end': 'combine',
            'host': 'combine',
            'administrator': 'combine',
            'url': 'combine',
            'language': 'combine',
            'reg_key': 'combine',
            'admin_fee': 'combine',
            'invoice_status': 'combine',
            'attendance': 'combine',
            'country': 'combine',
            'latitude': 'combine',
            'longitude': 'combine',
            'learners_pre': 'combine',
            'learners_post': 'combine',
            'instructors_pre': 'combine',
            'instructors_post': 'combine',
            'learners_longterm': 'combine',
        }
        # fields additionally accepting "combine"
        passing = {
            'tags': 'combine',
            'contact': 'combine',
            'venue': 'combine',
            'address': 'combine',
            'notes': 'combine',
            'task_set': 'combine',
            'todoitem_set': 'combine',
        }
        data = hidden.copy()
        data.update(failing)
        data.update(passing)

        form = EventsMergeForm(data)
        self.assertFalse(form.is_valid())

        for key in failing:
            self.assertIn(key, form.errors)
        for key in passing:
            self.assertNotIn(key, form.errors)

        # make sure no fields are added without this test being updated
        self.assertEqual(set(list(form.fields.keys())), set(list(data.keys())))

    def test_merging_base_event(self):
        """Merging: ensure the base event is selected based on ID form
        field.

        If ID field has a value of 'obj_b', then event B is base event and it
        won't be removed from the database after the merge. Event A, on the
        other hand, will."""
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)

        self.event_b.refresh_from_db()
        with self.assertRaises(Event.DoesNotExist):
            self.event_a.refresh_from_db()

    def test_merging_basic_attributes(self):
        """Merging: ensure basic (non-relationships) attributes are properly
        saved."""
        assertions = {
            'id': self.event_b.id,
            'slug': self.event_a.slug,
            'completed': self.event_b.completed,
            'assigned_to': self.event_a.assigned_to,
            'start': self.event_b.start,
            'end': self.event_a.end,
            'host': self.event_b.host,
            'administrator': self.event_a.administrator,
            'url': self.event_b.url,
            'language': self.event_b.language,
            'reg_key': self.event_a.reg_key,
            'admin_fee': self.event_b.admin_fee,
            'invoice_status': self.event_a.invoice_status,
            'attendance': self.event_b.attendance,
            'country': self.event_a.country,
            'latitude': self.event_b.latitude,
            'longitude': self.event_a.longitude,
            'learners_pre': self.event_b.learners_pre,
            'learners_post': self.event_a.learners_post,
            'instructors_pre': self.event_b.instructors_pre,
            'instructors_post': self.event_a.instructors_post,
            'learners_longterm': self.event_b.learners_longterm,
            'contact': self.event_a.contact,
            'venue': self.event_b.venue,
            'notes': self.event_a.notes,
            'address': self.event_a.address + self.event_b.address,
        }
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.event_b.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(getattr(self.event_b, key), value, key)

    def test_merging_relational_attributes(self):
        """Merging: ensure relational fields are properly saved/combined."""
        assertions = {
            'tags': set(Tag.objects.filter(name__in=['SWC', 'DC', 'LC'])),
            'task_set': set(Task.objects.none()),
            'todoitem_set': set(TodoItem.objects
                                        .filter(title='Find instructors')),
        }

        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.event_b.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(set(getattr(self.event_b, key).all()), value, key)

    def test_merging_m2m_attributes(self):
        """Merging: ensure M2M-related fields are properly saved/combined.
        This is a regression test; we have to ensure that M2M objects aren't
        removed from the database."""
        assertions = {
            'tags': set(Tag.objects.filter(name__in=['SWC'])),
        }
        self.strategy.update({
            'id': 'obj_a',
            'tags': 'obj_b',
        })

        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.event_a.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(set(getattr(self.event_a, key).all()), value, key)

    def test_merging_m2m_not_removed(self):
        """Regression test: merging events could result in M2M fields being
        removed, for example this could happen to Tags.
        This tests makes sure no M2M relation objects are being removed."""
        # update strategy
        self.strategy.update({
            'id': 'obj_b',
            'tags': 'obj_b',
        })
        # merge
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)

        # ensure no Tags were removed
        self.assertEqual(
            Tag.objects.filter(name__in=['LC', 'DC', 'SWC']).count(),
            3
        )



class TestEventImport(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

    def test_no_exception_when_empty_url(self):
        """Regression test: ensure no exceptions are raised when accessing
        `event_import` view without `url` GET param."""
        url = reverse('event_import')
        rv = self.client.get(url)
        self.assertLess(rv.status_code, 500)


class TestEventReviewingRepoChanges(TestBase):
    """Ensure views used for reviewing, accepting and dismissing changes made
    to event's metadata work correctly."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpOrganizations()

        self.cmd = WebsiteUpdatesCommand()

        self.metadata = {
            'slug': '2015-07-13-test',
            'language': 'US',
            'start': date(2015, 7, 13),
            'end': date(2015, 7, 14),
            'country': 'US',
            'venue': 'Euphoric State University',
            'address': 'Highway to Heaven 42, Academipolis',
            'latitude': 36.998977,
            'longitude': -109.045173,
            'reg_key': '10000000',
            'instructors': ['Hermione Granger', 'Ron Weasley'],
            'helpers': ['Peter Parker', 'Tony Stark', 'Natasha Romanova'],
            'contact': 'hermione@granger.co.uk, rweasley@ministry.gov',
        }
        self.metadata_serialized = self.cmd.serialize(self.metadata)

        # create event with some changes detected
        self.event = Event.objects.create(
            slug='event-for-changes', start=date(2016, 4, 20),
            end=date(2016, 4, 22), host=Organization.objects.first(),
            metadata_changed=True)

        # add metadata to the session
        session = self.client.session
        session['metadata_from_event_website'] = self.metadata_serialized
        session.save()

    def test_showing_all_events_with_changed_metadata(self):
        """Ensure `events_metadata_changed` only shows events with changed
        metadata."""
        url = reverse('events_metadata_changed')
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        self.assertEqual(list(rv.context['events']), [self.event])

    def test_accepting_changes(self):
        """Ensure `event_review_repo_changes_accept`:
        * updates changed values in event
        * dismisses notification about changed metadata
        * removes metadata from session
        * redirects to the event details page."""
        url = reverse('event_accept_metadata_changes',
                      args=[self.event.slug])
        rv = self.client.get(url, follow=False)

        # check for redirect to event's details page
        self.assertEqual(rv.status_code, 302)

        self.event.refresh_from_db()

        self.assertEqual(self.event.metadata_changed, False)
        self.assertEqual(self.event.metadata_all_changes, '')
        self.assertEqual(self.event.repository_metadata, self.metadata_serialized)
        for key, value in self.metadata.items():
            if key not in ('slug', 'instructors', 'helpers', 'language'):
                self.assertEqual(getattr(self.event, key), value)

    def test_accepting_changes_no_session_data(self):
        """Ensure `event_review_repo_changes_accept` throws 404 when specific
        session key 'metadata_from_event_website' is unavailable."""
        session = self.client.session
        del session['metadata_from_event_website']
        session.save()

        url = reverse('event_accept_metadata_changes',
                      args=[self.event.slug])
        rv = self.client.get(url, follow=False)
        self.assertEqual(rv.status_code, 404)

    def test_dismissing_changes(self):
        url = reverse('event_dismiss_metadata_changes',
                      args=[self.event.slug])
        rv = self.client.get(url, follow=False)

        # check for redirect to event's details page
        self.assertEqual(rv.status_code, 302)

        self.event.refresh_from_db()

        self.assertEqual(self.event.metadata_changed, False)
        self.assertEqual(self.event.metadata_all_changes, '')
        for key, value in self.metadata.items():
            if key not in ('slug', 'instructors', 'helpers', 'language'):
                self.assertNotEqual(getattr(self.event, key), value)
