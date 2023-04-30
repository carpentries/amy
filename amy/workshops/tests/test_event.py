from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.db import connection
from django.db.utils import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django_comments.models import Comment

from autoemails.actions import (
    AskForWebsiteAction,
    InstructorsHostIntroductionAction,
    PostWorkshopAction,
    RecruitHelpersAction,
)
from autoemails.models import EmailTemplate, RQJob, Trigger
from autoemails.tests.base import FakeRedisTestCaseMixin
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from workshops.forms import EventCreateForm, EventForm, EventsMergeForm
from workshops.models import (
    Award,
    Badge,
    Curriculum,
    Event,
    Organization,
    Person,
    Role,
    Tag,
    Task,
)
from workshops.tests.base import SuperuserMixin, TestBase
from workshops.utils.metadata import metadata_serialize
import workshops.views


class TestEvent(TestBase):
    "Tests for the event model and its manager."

    def setUp(self):
        self._setUpAirports()
        self._setUpNonInstructors()
        self._setUpUsersAndLogin()
        self._setUpOrganizations()
        self._setUpRoles()
        self._setUpTags()

        self.TTT_tag = Tag.objects.get(name="TTT")
        self.learner_role = Role.objects.get(name="learner")

        # Create a test tag
        self.test_tag = Tag.objects.create(name="Test Tag", details="For testing")

        # Create a test role
        Role.objects.create(name="Test Role")

        # Set up generic events.
        self._setUpEvents()

    def test_online_country_enforced_values(self):
        """Ensure that events from 'Online' country (W3) get some location data
        forced upon `save()`."""
        e = Event.objects.create(
            slug="online-event", country="W3", host=Organization.objects.first()
        )
        self.assertEqual(e.venue, "Internet")
        self.assertEqual(e.address, "Internet")
        self.assertEqual(e.latitude, None)
        self.assertEqual(e.longitude, None)

        e = Event.objects.create(
            slug="offline-event", country="US", host=Organization.objects.first()
        )
        self.assertNotEqual(e.venue, "Internet")
        self.assertNotEqual(e.address, "Internet")
        self.assertIsNone(e.latitude)
        self.assertIsNone(e.longitude)

    def test_get_upcoming_events(self):
        """Test that the events manager can find upcoming events"""

        upcoming_events = Event.objects.upcoming_events()
        expected = Event.objects.filter(slug__endswith="upcoming")
        self.assertEqual(set(upcoming_events), set(expected))

    def test_get_past_events(self):
        """Test that the events manager can find past events"""

        past_events = Event.objects.past_events()

        assert len(past_events) == 9

        # They should all start with past
        assert all(["past" in e.slug for e in past_events])

    def test_get_ongoing_events(self):
        """Test the events manager can find all events overlapping today.

        Include events that (according to the timestamp) are not ongoing,
        but which started or finished today.
        """

        ongoing_events = Event.objects.ongoing_events()
        event_slugs = [e.slug for e in ongoing_events]
        correct_slugs = ["ends-tomorrow-ongoing", "ends-today-ongoing"]

        self.assertCountEqual(event_slugs, correct_slugs)

    def test_unpublished_events(self):
        """Ensure that events manager finds unpublished events correctly."""
        expected = (
            Event.objects.exclude(slug__endswith="upcoming")
            .exclude(slug__in=["ends-today-ongoing", "ends-tomorrow-ongoing"])
            .exclude(slug__endswith="cancelled")
        )
        self.assertEqual(set(Event.objects.unpublished_events()), set(expected))

        event_considered_published = Event.objects.create(
            slug="published",
            start=date.today() + timedelta(days=3),
            end=date.today() + timedelta(days=6),
            latitude=-10.0,
            longitude=10.0,
            country="US",
            venue="University",
            address="Phenomenal Street",
            url="http://url/",
            host=Organization.objects.all().first(),
        )
        self.assertNotIn(event_considered_published, Event.objects.unpublished_events())

    def test_unpublished_events_displayed_once(self):
        """Regression test: unpublished events can't be displayed more than
        once on the dashboard.  Refer to #977."""
        unpublished_event = Event.objects.create(
            slug="2016-10-20-unpublished",
            start=date(2016, 10, 20),
            end=date(2016, 10, 21),
            host=Organization.objects.first(),
            administrator=Organization.objects.first(),
        )
        unpublished_event.tags.set(Tag.objects.filter(name__in=["TTT", "online"]))

        unpublished = Event.objects.unpublished_events().select_related("host")
        self.assertIn(unpublished_event, unpublished)
        self.assertEqual(1, len(unpublished.filter(slug="2016-10-20-unpublished")))

    def test_cancelled_events(self):
        """Regression test: make sure that cancelled events don't show up in
        the unpublished, or published events."""
        cancelled_event = Event.objects.create(
            slug="2017-01-07-cancelled",
            start=date(2017, 1, 7),
            end=date(2017, 1, 8),
            host=Organization.objects.first(),
            administrator=Organization.objects.first(),
        )
        cancelled_event.tags.set(Tag.objects.filter(name="cancelled"))

        published = Event.objects.published_events().select_related("host")
        unpublished = Event.objects.unpublished_events().select_related("host")
        self.assertNotIn(cancelled_event, published)
        self.assertNotIn(cancelled_event, unpublished)

    def test_delete_event(self):
        """Make sure deleted event without any tasks is no longer accessible."""
        event = Event.objects.get(slug="starts-today-ongoing")

        rv = self.client.post(reverse("event_delete", args=[event.slug]))
        self.assertEqual(rv.status_code, 302)

        with self.assertRaises(Event.DoesNotExist):
            Event.objects.get(slug="starts-today-ongoing")

    def test_delete_event_with_tasks_and_awards(self):
        """Ensure we cannot delete an event with related tasks and awards.

        Deletion is prevented via Award.event's on_delete=PROTECT
        and Task.event's on_delete=PROTECT."""
        event = Event.objects.get(slug="starts-today-ongoing")
        role = Role.objects.create(name="NonInstructor")
        badge = Badge.objects.create(
            name="noninstructor", title="Non-instructor", criteria=""
        )
        task = Task.objects.create(event=event, person=self.spiderman, role=role)
        award = Award.objects.create(
            person=self.spiderman, badge=badge, awarded=date.today(), event=event
        )

        rv = self.client.post(reverse("event_delete", args=[event.slug]))
        self.assertEqual(rv.status_code, 200)

        content = rv.content.decode("utf-8")
        self.assertIn("Failed to delete", content)
        self.assertIn("tasks", content)
        # not available since it's not propagated by Django
        # to ProtectedError.protected_objects
        # self.assertIn("awards", content)
        # make sure these objects were not deleted
        Event.objects.get(pk=event.pk)
        Badge.objects.get(pk=badge.pk)
        Task.objects.get(pk=task.pk)
        Award.objects.get(pk=award.pk)

    def test_repository_website_url(self):
        test_host = Organization.objects.all()[0]
        links = [
            "http://user-name.github.com/repo-name",
            "http://user-name.github.io/repo-name",
            "https://user-name.github.com/repo-name",
            "https://user-name.github.io/repo-name",
            "http://user-name.github.com/repo-name/",
            "http://user-name.github.io/repo-name/",
            "https://user-name.github.com/repo-name/",
            "https://user-name.github.io/repo-name/",
            "http://github.com/user-name/repo-name",
            "http://github.com/user-name/repo-name/",
            "https://github.com/user-name/repo-name",
            "https://github.com/user-name/repo-name/",
        ]
        REPO = "https://github.com/user-name/repo-name"
        WEBSITE = "https://user-name.github.io/repo-name/"
        for index, link in enumerate(links):
            event = Event.objects.create(
                slug="e{}".format(index), host=test_host, url=link
            )
            assert event.repository_url == REPO
            assert event.website_url == WEBSITE

    def test_wrong_repository_website_urls(self):
        test_host = Organization.objects.all()[0]
        link = "http://en.wikipedia.org/"
        event = Event.objects.create(slug="test-event", host=test_host, url=link)
        assert event.repository_url == link
        assert event.website_url == link

    def test_open_TTT_applications_validation(self):
        event = Event.objects.create(
            slug="test-event",
            host=self.org_alpha,
            sponsor=self.org_alpha,
            administrator=self.org_alpha,
        )

        # without TTT tag, the validation fails
        event.open_TTT_applications = True
        with self.assertRaises(ValidationError) as cm:
            event.full_clean()
        exc = cm.exception
        self.assertIn("open_TTT_applications", exc.error_dict)

        # now the validation should pass
        event.tags.set([self.TTT_tag])
        event.full_clean()

    def test_eligible_for_instructor_recruitment(self) -> None:
        # Arrange
        host = Organization.objects.first()
        online_tag = Tag.objects.get(name="online")
        data = [
            (Event(slug="test1", host=host, start=date(2000, 1, 1)), False),
            (Event.objects.create(slug="test2", host=host, start=date.today()), False),
            (Event.objects.create(slug="test3", host=host, start=date.today()), True),
            (
                Event.objects.create(
                    slug="test4", host=host, start=date.today(), venue="University"
                ),
                False,
            ),
            (
                Event.objects.create(
                    slug="test5",
                    host=host,
                    start=date.today(),
                    venue="University",
                    latitude=1,
                ),
                False,
            ),
            (
                Event.objects.create(
                    slug="test6",
                    host=host,
                    start=date.today(),
                    venue="University",
                    latitude=1,
                    longitude=-1,
                ),
                True,
            ),
            (
                Event.objects.create(slug="test1", host=host, start=date(2000, 1, 1)),
                False,
            ),
        ]
        data[2][0].tags.add(online_tag)
        data[6][0].tags.add(online_tag)

        for event, expected in data:
            # Act
            result = event.eligible_for_instructor_recruitment()

            # Assert
            self.assertEqual(result, expected, event)


class TestEventFormComments(TestBase):
    form = EventForm

    def setUp(self):
        self._setUpOrganizations()
        self.test_tag = Tag.objects.create(name="Test Tag", details="For testing")

    def test_creating_event_with_no_comment(self):
        """Ensure that no comment is added when the form without comment
        content is saved."""
        self.assertEqual(Comment.objects.count(), 0)
        data = {
            "slug": "2018-12-28-test-event",
            "host": self.org_alpha.id,
            "sponsor": self.org_alpha.id,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [self.test_tag.id],
            "comment": "",
        }
        form = EventForm(data)
        form.save()
        self.assertEqual(Comment.objects.count(), 0)

    def test_creating_event_with_comment(self):
        """Ensure that a comment is added when the form with comment
        content is saved."""
        self.assertEqual(Comment.objects.count(), 0)
        data = {
            "slug": "2018-12-28-test-event",
            "host": self.org_alpha.id,
            "sponsor": self.org_alpha.id,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [self.test_tag.id],
            "comment": "This is a test comment.",
        }
        form = EventForm(data)
        obj = form.save()
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()
        self.assertEqual(comment.comment, "This is a test comment.")
        self.assertIn(comment, Comment.objects.for_model(obj))


class TestEventCreateFormComments(TestEventFormComments):
    form = EventCreateForm


class TestEventManager(TestBase):
    def test_ttt(self):
        org = Organization.objects.create(
            domain="example.com", fullname="Test Organization"
        )
        ttt_tag = Tag.objects.create(name="TTT")
        _ = Event.objects.create(slug="first", host=org)
        second = Event.objects.create(slug="second", host=org)
        second.tags.add(ttt_tag)
        third = Event.objects.create(slug="third", host=org)
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

        self.learner = Role.objects.get_or_create(name="learner")[0]

        # Create a test host
        self.test_host = Organization.objects.create(
            domain="example.com", fullname="Test Organization"
        )

        # Create a test tag
        self.test_tag = Tag.objects.create(name="Test Tag", details="For testing")

        # Create fifty new events
        for i in range(50):
            event_start = datetime.now()
            Event.objects.create(
                start=event_start,
                slug="test_event_{0}".format(i),
                host=self.test_host,
                sponsor=self.test_host,
            )

    def test_events_view_paginated(self):

        events_url = reverse("all_events")
        events_url += "?items_per_page=10"
        response = self.client.get(events_url)

        # We asked for max 10 events, make sure we got them
        view_events = response.context["all_events"]

        assert len(view_events) == 10

    def test_can_request_all_events(self):

        events_url = reverse("all_events")
        events_url += "?items_per_page=all"
        response = self.client.get(events_url)

        # We asked for all events, make sure we got them
        view_events = response.context["all_events"]
        all_events = list(Event.objects.all())

        self.assertCountEqual(view_events, all_events)

    def test_invalid_items_per_page_gives_default_pagination(self):

        events_url = reverse("all_events")
        events_url += "?items_per_page=not_an_integer"
        response = self.client.get(events_url)

        # View should be paginated by default, so we shouldn't get all events
        view_events = response.context["all_events"]

        assert len(view_events) < 50

    def test_non_integer_page_no_returns_first_page(self):

        events_url = reverse("all_events")
        events_url += "?items_per_page=10&page=not_an_integer"
        response = self.client.get(events_url)

        # Get the events for this page
        view_events = response.context["all_events"]

        # They should still be paginated
        assert len(view_events) == 10

        # This should be the first page
        assert view_events.number == 1

    def test_page_no_too_large_returns_last_page(self):

        events_url = reverse("all_events")
        events_url += "?items_per_page=10&page=999"
        response = self.client.get(events_url)

        # Get the events for this page
        view_events = response.context["all_events"]

        # They should still be paginated
        assert len(view_events) == 10

        # This should be the first page
        assert view_events.number == 5

    def test_add_minimal_event(self):
        host = Organization.objects.get(fullname="Test Organization")
        # administrator can only be selected from `administrators`
        admin = Organization.objects.administrators().first()
        response = self.client.post(
            reverse("event_add"),
            {
                "slug": "2012-12-21-event-final",
                "host": host.id,
                "sponsor": host.id,
                "tags": [self.test_tag.id],
                "administrator": admin.id,
            },
        )

        self.assertEqual(response.status_code, 302)
        url = response["location"]
        event_slug = url.rstrip("/").rsplit("/", 1)[1]
        event = Event.objects.get(slug=event_slug)
        self.assertEqual(
            event.host,
            host,
            "New event has wrong host: {} != {}".format(event.host, host),
        )
        tags = list(event.tags.all())
        self.assertEqual(
            tags,
            [self.test_tag],
            "New event has wrong tags: {} != {}".format(tags, [self.test_tag]),
        )

    def test_unique_slug(self):
        """Ensure events with the same slugs are prohibited.

        This is a regression test for
        https://github.com/swcarpentry/amy/issues/427"""
        Event.objects.create(
            host=self.test_host, sponsor=self.test_host, slug="testing-unique-slug"
        )
        with self.assertRaises(IntegrityError):
            Event.objects.create(
                host=self.test_host, sponsor=self.test_host, slug="testing-unique-slug"
            )

    def test_assign_to_field_populated(self):
        """Ensure that we can assign an admin to an event
        from the `event_add` view."""
        data = {
            "slug": "2016-07-09-test",
            "host": self.test_host.id,
            "sponsor": self.test_host.id,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [self.test_tag.id],
            "assigned_to": self.admin.pk,
        }
        response = self.client.post(reverse("event_add"), data, follow=True)
        event = Event.objects.get(slug="2016-07-09-test")
        self.assertRedirects(
            response,
            reverse("event_details", kwargs={"slug": event.slug}),
        )
        self.assertEqual(event.assigned_to, self.admin)

    def test_unique_non_empty_slug(self):
        """Ensure events with no slugs are *not* saved to the DB."""
        data = {
            "host": self.test_host.id,
            "sponsor": self.test_host.id,
            "tags": [self.test_tag.id],
            "slug": "",
        }
        response = self.client.post(reverse("event_add"), data)
        assert response.status_code == 200

    def test_start_date_gte_end_date(self):
        """Ensure event's start date is earlier than it's end date.

        This is a regression test for
        https://github.com/swcarpentry/amy/issues/436"""
        data = {
            "host": self.test_host.id,
            "sponsor": self.test_host.id,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [self.test_tag.id],
            "slug": "2016-06-30-test-event",
            "start": date(2015, 7, 20),
            "end": date(2015, 7, 19),
        }
        response = self.client.post(reverse("event_add"), data)
        assert response.status_code == 200
        content = response.content.decode("utf-8")
        assert "Must not be earlier than start date" in content

        data = {
            "host": self.test_host.id,
            "sponsor": self.test_host.id,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [self.test_tag.id],
            "slug": "2016-06-30-test-event",
            "start": date(2015, 7, 20),
            "end": date(2015, 7, 20),
        }
        response = self.client.post(reverse("event_add"), data)
        assert response.status_code == 302

        data = {
            "host": self.test_host.id,
            "sponsor": self.test_host.id,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [self.test_tag.id],
            "slug": "2016-06-30-test-event2",
            "start": date(2015, 7, 20),
            "end": date(2015, 7, 21),
        }
        response = self.client.post(reverse("event_add"), data)
        assert response.status_code == 302

    def test_negative_manual_attendance(self):
        """Ensure we disallow negative manual attendance.

        This is a regression test for
        https://github.com/swcarpentry/amy/issues/435."""
        error_str = "Ensure this value is greater than or equal to 0."

        data = {
            "host": self.test_host.id,
            "sponsor": self.test_host.id,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [self.test_tag.id],
            "slug": "2016-06-30-test-event",
            "manual_attendance": -36,
        }

        data["manual_attendance"] = -36
        f = EventForm(data)
        self.assertIn("manual_attendance", f.errors)
        self.assertIn(error_str, f.errors["manual_attendance"])

        data["manual_attendance"] = 0
        f = EventForm(data)
        self.assertNotIn("manual_attendance", f.errors)

        data["slug"] = "2016-06-30-test-event2"
        data["manual_attendance"] = 36
        f = EventForm(data)
        self.assertTrue(f.is_valid())

    def test_empty_manual_attendance(self):
        """Ensure we don't get 500 server error when field is left with empty
        value.

        This is a regression test for
        https://github.com/swcarpentry/amy/issues/1608."""

        data = {
            "slug": "2016-06-30-test-event",
            "host": self.test_host.id,
            "sponsor": self.test_host.id,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [self.test_tag.id],
            "manual_attendance": "",
        }
        f = EventForm(data)
        self.assertTrue(f.is_valid())
        event = f.save()
        self.assertEqual(event.manual_attendance, 0)

    def test_number_of_attendees_increasing(self):
        """Ensure event.attendance gets bigger after adding new learners."""
        event = Event.objects.get(slug="test_event_0")
        event.manual_attendance = 0  # testing for numeric case
        event.save()
        self.assertEqual(event.attendance, 0)

        data = {
            "task-role": self.learner.pk,
            "task-event": event.pk,
            "task-person": self.spiderman.pk,
        }
        self.client.post(reverse("task_add"), data)

        # instead of refreshing, we have to get a "fresh" object, because
        # `attendance` is a cached property
        event = Event.objects.get(slug="test_event_0")
        self.assertEqual(event.attendance, 1)

    def test_slug_illegal_characters(self):
        """Disallow slugs with wrong characters.

        Slug allows only: latin characters, numbers, dashes and underscores.
        Slug format should follow: YYYY-MM-DD-location, where YYYY, MM, DD can
        be unspecified (== 'xx')."""
        data = {
            "slug": "",
            "host": Organization.objects.all()[0].pk,
            "sponsor": Organization.objects.all()[0].pk,
            "tags": Tag.objects.all(),
        }

        # disallow illegal characters
        for slug_suffix in ["a/b", "a b", "a!b", "a.b", "a\\b", "a?b", "aób"]:
            with self.subTest(slug_suffix=slug_suffix):
                data["slug"] = "2016-06-30-{}".format(slug_suffix)
                f = EventForm(data)
                self.assertEqual(f.is_valid(), False)
                self.assertIn("slug", f.errors)

    def test_slug_illegal_formats(self):
        """Disallow slugs with wrong formats.

        Slug format should follow: YYYY-MM-DD-location, where YYYY, MM, DD can
        be unspecified (== 'xx')."""
        data = {
            "slug": "",
            "host": Organization.objects.all()[0].pk,
            "sponsor": Organization.objects.all()[0].pk,
            "tags": [Tag.objects.first().pk],
        }

        # disallow invalid formats
        formats = [
            "20166-06-30-Krakow",
            "2016-006-30-Krakow",
            "2016-06-300-Krakow",
            "201-06-30-Krakow",
            "2016-6-30-Krakow",
            "2016-06-3-Krakow",
            "SWC-2016-06-300-Krakow",
            "",
            "xxxxx-xx-xx-Krakow",
            "xxxx-xxx-xx-Krakow",
            "xxxx-xx-xxx-Krakow",
            "xxx-xx-xx-Krakow",
            "xxxx-x-xx-Krakow",
            "xxxx-xx-x-Krakow",
        ]
        for slug in formats:
            with self.subTest(slug=slug):
                data["slug"] = slug
                f = EventForm(data)
                self.assertEqual(f.is_valid(), False)
                self.assertIn("slug", f.errors)

    def test_slug_valid_formats(self):
        """Allow slugs with wrong formats.

        Slug format should follow: YYYY-MM-DD-location, where YYYY, MM, DD can
        be unspecified (== 'xx')."""
        data = {
            "slug": "",
            "host": Organization.objects.all()[0].pk,
            "sponsor": Organization.objects.all()[0].pk,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [Tag.objects.first().pk],
        }

        # allow correct formats
        formats = [
            "2016-06-30-Krakow",
            "2016-06-xx-Krakow",
            "2016-xx-30-Krakow",
            "xxxx-06-30-Krakow",
            "2016-xx-xx-Krakow",
            "xxxx-06-xx-Krakow",
            "xxxx-xx-30-Krakow",
            "xxxx-xx-xx-Krakow",
            "2016-06-30-Krakow-multiple-words",
            "2016-06-xx-Krakow-multiple-words",
            "2016-xx-30-Krakow-multiple-words",
            "xxxx-06-30-Krakow-multiple-words",
            "2016-xx-xx-Krakow-multiple-words",
            "xxxx-06-xx-Krakow-multiple-words",
            "xxxx-xx-30-Krakow-multiple-words",
            "xxxx-xx-xx-Krakow-multiple-words",
        ]
        for slug in formats:
            with self.subTest(slug=slug):
                data["slug"] = slug
                f = EventForm(data)
                self.assertEqual(f.is_valid(), True)
                self.assertNotIn("slug", f.errors)

    def test_display_of_event_without_start_date(self):
        """A bug prevented events without start date to throw a 404.

        This is a regression test against that bug.
        The error happened when "".format encountered None instead of
        datetime."""
        event = Event.objects.create(
            slug="regression_event_0", host=self.test_host, sponsor=self.test_host
        )
        rv = self.client.get(reverse("event_details", args=[event.slug]))
        assert rv.status_code == 200

    def test_open_TTT_applications_form_validation(self):
        """Ensure validation of `open_TTT_applications` field."""
        data = {
            "slug": "2018-09-02-open-applications",
            "host": self.org_alpha.pk,
            "sponsor": self.org_alpha.pk,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [Tag.objects.get(name="SWC").pk],
            "open_TTT_applications": True,
        }
        form = EventForm(data)
        self.assertFalse(form.is_valid())
        self.assertIn("open_TTT_applications", form.errors.keys())

        data["tags"] = [Tag.objects.get(name="TTT").pk]
        form = EventForm(data)
        self.assertTrue(form.is_valid())

    def test_curricula_and_tags_validation(self):
        """Ensure validation of `curricula` and `tags` fields."""
        # missing tags
        data = {
            "slug": "2018-10-28-curriculum",
            "host": self.org_alpha.pk,
            "sponsor": self.org_alpha.pk,
            "tags": [
                Tag.objects.get(name="TTT").pk,
                Tag.objects.get(name="online").pk,
            ],
            "curricula": [
                Curriculum.objects.get(slug="swc-python").pk,
                Curriculum.objects.get(slug="dc-geospatial").pk,
                Curriculum.objects.get(slug="lc").pk,
                # below isn't a valid choice
                # Curriculum.objects.get(unknown=True).pk,
            ],
        }
        form = EventForm(data)
        self.assertIn("tags", form.errors)

        # try adding SWC tag
        data["tags"].append(Tag.objects.get(name="SWC").pk)
        form = EventForm(data)
        self.assertIn("tags", form.errors)

        # try adding DC tag
        data["tags"].append(Tag.objects.get(name="DC").pk)
        form = EventForm(data)
        self.assertIn("tags", form.errors)

        # try adding LC tag
        data["tags"].append(Tag.objects.get(name="LC").pk)
        form = EventForm(data)
        self.assertNotIn("tags", form.errors)

    def test_curricula_circuits_tag(self):
        """Ensure validation of `curricula` and `tags` fields."""
        # missing tags
        data = {
            "slug": "2018-10-28-curriculum",
            "host": self.org_alpha.pk,
            "sponsor": self.org_alpha.pk,
            # there has to be some tag
            "tags": [Tag.objects.get(name="DC").pk],
            "curricula": [
                Curriculum.objects.get(slug="swc-python").pk,
                Curriculum.objects.get(mix_match=True).pk,
            ],
        }
        form = EventForm(data)
        # we're missing SWC and Circuits
        self.assertIn("tags", form.errors)

        # try adding SWC tag
        data["tags"].append(Tag.objects.get(name="SWC").pk)
        form = EventForm(data)
        self.assertIn("tags", form.errors)
        # now we're missing only circuits

        # try adding Circuits tag
        data["tags"].append(Tag.objects.get(name="Circuits").pk)
        form = EventForm(data)
        self.assertNotIn("tags", form.errors)

    def test_event_recruitment_statistics(self):
        # Arrange
        host = Organization.objects.get(fullname="Test Organization")
        admin = Organization.objects.administrators().first()
        event = Event.objects.create(
            slug="2021-12-19-event-recruitment",
            host=host,
            sponsor=host,
            administrator=admin,
        )
        recruitment = InstructorRecruitment.objects.create(event=event)
        InstructorRecruitmentSignup.objects.bulk_create(
            [
                InstructorRecruitmentSignup(
                    recruitment=recruitment,
                    person=self.spiderman,
                    interest="part",
                    state="a",
                ),
                InstructorRecruitmentSignup(
                    recruitment=recruitment,
                    person=self.spiderman,
                    interest="session",
                    state="p",
                ),
                InstructorRecruitmentSignup(
                    recruitment=recruitment,
                    person=self.ironman,
                    interest="session",
                    state="a",
                ),
                InstructorRecruitmentSignup(
                    recruitment=recruitment,
                    person=self.blackwidow,
                    interest="session",
                    state="d",
                ),
            ]
        )
        # Act
        response = self.client.get(event.get_absolute_url())
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIn("recruitment_stats", response.context)
        self.assertEqual(
            response.context["recruitment_stats"],
            {
                "all_signups": 4,
                "pending_signups": 1,
                "discarded_signups": 1,
                "accepted_signups": 2,
            },
        )


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
        self._setUpSites()

        today = date.today()
        tomorrow = today + timedelta(days=1)

        # Add full-blown events so that we can test merging of everything.
        # Random data such as contact, venue, address, lat/long, or URLs
        # were generated with faker (see `fake_database.py` for details).
        self.event_a = Event.objects.create(
            slug="event-a",
            completed=True,
            assigned_to=self.harry,
            start=today,
            end=tomorrow,
            host=self.org_alpha,
            sponsor=self.org_alpha,
            administrator=self.org_alpha,
            public_status="public",
            url="http://reichel.com/event-a",
            language=self.french,
            reg_key="123456",
            manual_attendance=30,
            contact="moore.buna@schuppe.info",
            country="US",
            venue="Modi",
            address="876 Dot Fork",
            latitude=59.987509,
            longitude=-51.507076,
            learners_pre="http://reichel.com/learners_pre",
            learners_post="http://reichel.com/learners_post",
            instructors_pre="http://reichel.com/instructors_pre",
            instructors_post="http://reichel.com/instructors_post",
            learners_longterm="http://reichel.com/learners_longterm",
        )
        self.event_a.tags.set(Tag.objects.filter(name__in=["LC", "DC"]))
        self.event_a.task_set.create(
            person=self.harry, role=Role.objects.get(name="instructor")
        )
        # comments regarding this event
        self.ca = Comment.objects.create(
            content_object=self.event_a,
            user=self.harry,
            comment="Comment from admin on event_a",
            submit_date=datetime.now(tz=timezone.utc),
            site=self.current_site,
        )

        self.event_b = Event.objects.create(
            slug="event-b",
            completed=False,
            assigned_to=self.hermione,
            start=today,
            end=tomorrow + timedelta(days=1),
            host=self.org_beta,
            sponsor=self.org_beta,
            administrator=self.org_beta,
            public_status="private",
            url="http://www.cummings.biz/event-b",
            language=self.english,
            reg_key="654321",
            manual_attendance=40,
            contact="haleigh.schneider@hotmail.com",
            country="GB",
            venue="Nisi",
            address="59747 Fernanda Cape",
            latitude=-29.545137,
            longitude=32.417491,
            learners_pre="http://www.cummings.biz/learners_pre",
            learners_post="http://www.cummings.biz/learners_post",
            instructors_pre="http://www.cummings.biz/instructors_pre",
            instructors_post="http://www.cummings.biz/instructors_post",
            learners_longterm="http://www.cummings.biz/learners_longterm",
        )
        self.event_b.tags.set(Tag.objects.filter(name="SWC"))
        # no tasks for this event
        # comments regarding this event
        self.cb = Comment.objects.create(
            content_object=self.event_b,
            user=self.hermione,
            comment="Comment from admin on event_b",
            submit_date=datetime.now(tz=timezone.utc),
            site=self.current_site,
        )

        # some "random" strategy for testing
        self.strategy = {
            "event_a": self.event_a.pk,
            "event_b": self.event_b.pk,
            "id": "obj_b",
            "slug": "obj_a",
            "completed": "obj_b",
            "assigned_to": "obj_a",
            "start": "obj_b",
            "end": "obj_a",
            "host": "obj_b",
            "sponsor": "obj_b",
            "administrator": "obj_a",
            "public_status": "obj_a",
            "url": "obj_b",
            "language": "obj_b",
            "reg_key": "obj_a",
            "manual_attendance": "obj_b",
            "country": "obj_a",
            "latitude": "obj_b",
            "longitude": "obj_a",
            "learners_pre": "obj_b",
            "learners_post": "obj_a",
            "instructors_pre": "obj_b",
            "instructors_post": "obj_a",
            "learners_longterm": "obj_b",
            "contact": "obj_a",
            "venue": "obj_b",
            "address": "combine",
            "tags": "combine",
            "task_set": "obj_b",
            "comments": "combine",
        }
        base_url = reverse("events_merge")
        query = urlencode({"event_a": self.event_a.pk, "event_b": self.event_b.pk})
        self.url = "{}?{}".format(base_url, query)

    def test_form_invalid_values(self):
        """Make sure only a few fields accept third option ("combine")."""
        hidden = {
            "event_a": self.event_a.pk,
            "event_b": self.event_b.pk,
        }
        # fields accepting only 2 options: "obj_a" and "obj_b"
        failing = {
            "id": "combine",
            "slug": "combine",
            "completed": "combine",
            "assigned_to": "combine",
            "start": "combine",
            "end": "combine",
            "host": "combine",
            "sponsor": "combine",
            "administrator": "combine",
            "public_status": "combine",
            "url": "combine",
            "language": "combine",
            "reg_key": "combine",
            "manual_attendance": "combine",
            "country": "combine",
            "latitude": "combine",
            "longitude": "combine",
            "learners_pre": "combine",
            "learners_post": "combine",
            "instructors_pre": "combine",
            "instructors_post": "combine",
            "learners_longterm": "combine",
        }
        # fields additionally accepting "combine"
        passing = {
            "tags": "combine",
            "contact": "combine",
            "venue": "combine",
            "address": "combine",
            "task_set": "combine",
            "comments": "combine",
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
            "id": self.event_b.id,
            "slug": self.event_a.slug,
            "completed": self.event_b.completed,
            "assigned_to": self.event_a.assigned_to,
            "start": self.event_b.start,
            "end": self.event_a.end,
            "host": self.event_b.host,
            "sponsor": self.event_b.sponsor,
            "administrator": self.event_a.administrator,
            "public_status": self.event_a.public_status,
            "url": self.event_b.url,
            "language": self.event_b.language,
            "reg_key": self.event_a.reg_key,
            "manual_attendance": self.event_b.manual_attendance,
            "country": self.event_a.country,
            "latitude": self.event_b.latitude,
            "longitude": self.event_a.longitude,
            "learners_pre": self.event_b.learners_pre,
            "learners_post": self.event_a.learners_post,
            "instructors_pre": self.event_b.instructors_pre,
            "instructors_post": self.event_a.instructors_post,
            "learners_longterm": self.event_b.learners_longterm,
            "contact": self.event_a.contact,
            "venue": self.event_b.venue,
            "address": self.event_a.address + self.event_b.address,
        }
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.event_b.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(getattr(self.event_b, key), value, key)

    def test_merging_relational_attributes(self):
        """Merging: ensure relational fields are properly saved/combined."""
        assertions = {
            "tags": set(Tag.objects.filter(name__in=["SWC", "DC", "LC"])),
            "task_set": set(Task.objects.none()),
            # comments are not relational, they're related via generic FKs,
            # so they won't appear here
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
            "tags": set(Tag.objects.filter(name__in=["SWC"])),
        }
        self.strategy.update({"id": "obj_a", "tags": "obj_b"})

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
        self.strategy.update({"id": "obj_b", "tags": "obj_b"})
        # merge
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)

        # ensure no Tags were removed
        self.assertEqual(Tag.objects.filter(name__in=["LC", "DC", "SWC"]).count(), 3)

    def test_merging_comments_strategy1(self):
        """Ensure comments are correctly merged using `merge_objects`.
        This test uses strategy 1 (combine)."""
        self.strategy["comments"] = "combine"
        comments = [self.ca, self.cb]
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.event_b.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.event_b).filter(is_removed=False)),
            set(comments),
        )

    def test_merging_comments_strategy2(self):
        """Ensure comments are correctly merged using `merge_objects`.
        This test uses strategy 2 (object a)."""
        self.strategy["comments"] = "obj_a"
        comments = [self.ca]
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.event_b.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.event_b).filter(is_removed=False)),
            set(comments),
        )

    def test_merging_comments_strategy3(self):
        """Ensure comments are correctly merged using `merge_objects`.
        This test uses strategy 3 (object b)."""
        self.strategy["comments"] = "obj_b"
        comments = [self.cb]
        rv = self.client.post(self.url, data=self.strategy)
        self.assertEqual(rv.status_code, 302)
        self.event_b.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.event_b).filter(is_removed=False)),
            set(comments),
        )


class TestEventImport(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

    def test_no_exception_when_empty_url(self):
        """Regression test: ensure no exceptions are raised when accessing
        `event_import` view without `url` GET param."""
        url = reverse("event_import")
        rv = self.client.get(url)
        self.assertLess(rv.status_code, 500)


class TestEventReviewingRepoChanges(TestBase):
    """Ensure views used for reviewing, accepting and dismissing changes made
    to event's metadata work correctly."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpOrganizations()

        self.metadata = {
            "slug": "2015-07-13-test",
            "language": "US",
            "start": date(2015, 7, 13),
            "end": date(2015, 7, 14),
            "country": "US",
            "venue": "Euphoric State University",
            "address": "Highway to Heaven 42, Academipolis",
            "latitude": 36.998977,
            "longitude": -109.045173,
            "reg_key": "10000000",
            "instructors": ["Hermione Granger", "Ron Weasley"],
            "helpers": ["Peter Parker", "Tony Stark", "Natasha Romanova"],
            "contact": "hermione@granger.co.uk, rweasley@ministry.gov",
        }
        self.metadata_serialized = metadata_serialize(self.metadata)

        # create event with some changes detected
        self.event = Event.objects.create(
            slug="event-for-changes",
            start=date(2016, 4, 20),
            end=date(2016, 4, 22),
            host=Organization.objects.first(),
            metadata_changed=True,
        )

        # add metadata to the session
        session = self.client.session
        session["metadata_from_event_website"] = self.metadata_serialized
        session.save()

    def test_showing_all_events_with_changed_metadata(self):
        """Ensure `events_metadata_changed` only shows events with changed
        metadata."""
        url = reverse("events_metadata_changed")
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        self.assertEqual(list(rv.context["events"]), [self.event])

    def test_accepting_changes(self):
        """Ensure `event_review_repo_changes_accept`:
        * updates changed values in event
        * dismisses notification about changed metadata
        * removes metadata from session
        * redirects to the event details page."""
        url = reverse("event_accept_metadata_changes", args=[self.event.slug])
        rv = self.client.get(url, follow=False)

        # check for redirect to event's details page
        self.assertEqual(rv.status_code, 302)

        self.event.refresh_from_db()

        self.assertEqual(self.event.metadata_changed, False)
        self.assertEqual(self.event.metadata_all_changes, "")
        self.assertEqual(self.event.repository_metadata, self.metadata_serialized)
        for key, value in self.metadata.items():
            if key not in ("slug", "instructors", "helpers", "language"):
                self.assertEqual(getattr(self.event, key), value)

    def test_accepting_changes_no_session_data(self):
        """Ensure `event_review_repo_changes_accept` throws 404 when specific
        session key 'metadata_from_event_website' is unavailable."""
        session = self.client.session
        del session["metadata_from_event_website"]
        session.save()

        url = reverse("event_accept_metadata_changes", args=[self.event.slug])
        rv = self.client.get(url, follow=False)
        self.assertEqual(rv.status_code, 404)

    def test_dismissing_changes(self):
        url = reverse("event_dismiss_metadata_changes", args=[self.event.slug])
        rv = self.client.get(url, follow=False)

        # check for redirect to event's details page
        self.assertEqual(rv.status_code, 302)

        self.event.refresh_from_db()

        self.assertEqual(self.event.metadata_changed, False)
        self.assertEqual(self.event.metadata_all_changes, "")
        for key, value in self.metadata.items():
            if key not in ("slug", "instructors", "helpers", "language"):
                self.assertNotEqual(getattr(self.event, key), value)


class TestEventAttendance(TestBase):
    """
    Make sure new (as of #1177) attendance mechanics work as expected.
    """

    _db_engine = connection.settings_dict["ENGINE"]

    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        self.slug = "2019-03-19-simple-event"
        self.event = Event.objects.create(
            slug=self.slug,
            country="US",
            host=Organization.objects.first(),
            sponsor=Organization.objects.first(),
            administrator=Organization.objects.first(),
        )
        self.event.tags.set(Tag.objects.filter(name__in=["LC", "DC"]))

    def test_correct_values_for_manual_attendance(self):
        # `manual_attendance` doesn't accept anything below 0
        with self.assertRaises(ValidationError):
            self.event.manual_attendance = -2
            self.event.full_clean()  # manually trigger validation

        self.event.manual_attendance = 0
        self.event.full_clean()  # manually trigger validation

    def test_zero_attendance(self):
        # manual_attendance = 0
        # some tasks, but none of them is learner
        # attendance == 0
        self.event.manual_attendance = 0
        self.event.save()
        self.event.task_set.create(
            person=self.hermione, role=Role.objects.get(name="instructor")
        )
        self.event.task_set.create(
            person=self.ron, role=Role.objects.get(name="helper")
        )
        self.assertEqual(Event.objects.attendance().get(slug=self.slug).attendance, 0)

    def test_single_manual_attendance(self):
        self.event.manual_attendance = 1
        self.event.save()
        self.assertEqual(self.event.task_set.count(), 0)
        self.assertEqual(self.event.attendance, 1)

    def test_single_learner_task(self):
        self.event.manual_attendance = 0
        self.event.save()
        self.event.task_set.create(
            person=self.harry, role=Role.objects.get(name="learner")
        )
        self.assertEqual(self.event.attendance, 1)

    def test_equal_manual_attendance_and_learner_tasks(self):
        # manual_attendance = 2
        # 2 learner tasks
        # attendance = 2
        self.event.manual_attendance = 2
        self.event.save()
        self.event.task_set.create(
            person=self.harry, role=Role.objects.get(name="learner")
        )
        self.event.task_set.create(
            person=self.spiderman, role=Role.objects.get(name="learner")
        )
        self.assertEqual(self.event.attendance, 2)


class TestEventCreatePostWorkshopAction(
    FakeRedisTestCaseMixin, SuperuserMixin, TestCase
):
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
        Tag.objects.bulk_create(
            [
                Tag(name="SWC"),
                Tag(name="DC"),
                Tag(name="LC"),
                Tag(name="automated-email"),
            ]
        )

        self.LC_org = Organization.objects.create(
            domain="librarycarpentry.org",
            fullname="Library Carpentry",
        )

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(
            action="week-after-workshop-completion",
            template=template,
        )

    def test_job_scheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # no events
        self.assertFalse(Event.objects.all())
        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        self.client.force_login(self.admin)
        data = {
            "slug": "2020-02-07-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "start": date.today(),
            "end": date.today() + timedelta(days=2),
            "administrator": self.LC_org.pk,
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(reverse("event_add"), data, follow=True)
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        self.assertContains(
            response,
            "New email (7 days past the end date of an active workshop) was scheduled",
        )

        # new event appeared
        self.assertEqual(Event.objects.count(), 1)

        # ensure the new event passes action checks
        event = Event.objects.first()
        self.assertTrue(PostWorkshopAction.check(event))

        # 1 new jobs
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjobs
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)


class TestEventUpdatePostWorkshopAction(
    FakeRedisTestCaseMixin, SuperuserMixin, TestCase
):
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
        Tag.objects.bulk_create(
            [
                Tag(name="SWC"),
                Tag(name="DC"),
                Tag(name="LC"),
                Tag(name="automated-email"),
            ]
        )

        self.LC_org = Organization.objects.create(
            domain="librarycarpentry.org",
            fullname="Library Carpentry",
        )

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(
            action="week-after-workshop-completion",
            template=template,
        )

    def test_job_scheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # this event shouldn't trigger action
        event = Event.objects.create(
            slug="2020-02-07-test-event",
            host=Organization.objects.first(),
            sponsor=Organization.objects.first(),
            start=None,
            end=None,
            administrator=self.LC_org,
        )
        event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        self.assertFalse(PostWorkshopAction.check(event))

        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        # add start & end date and save
        self.client.force_login(self.admin)
        data = {
            "slug": "2020-02-07-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "start": date.today(),
            "end": date.today() + timedelta(days=2),
            "administrator": self.LC_org.pk,
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        self.assertContains(
            response,
            "New email (7 days past the end date of an active workshop) was scheduled",
        )

        event.refresh_from_db()
        self.assertTrue(PostWorkshopAction.check(event))

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

        # this event won't trigger an action if we created it via a view
        event = Event.objects.create(
            slug="2020-02-07-test-event",
            host=Organization.objects.first(),
            sponsor=Organization.objects.first(),
            start=None,
            end=None,
            administrator=self.LC_org,
        )
        event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        self.assertFalse(PostWorkshopAction.check(event))

        # no jobs - again, due to not creating via WWW
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs - again, due to not creating via WWW
        self.assertFalse(RQJob.objects.all())

        # change event's start and end dates
        self.client.force_login(self.admin)
        data = {
            "slug": "2020-02-07-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "start": date.today(),
            "end": date.today() + timedelta(days=2),
            "administrator": self.LC_org.pk,
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        self.assertContains(
            response,
            "New email (7 days past the end date of an active workshop) was scheduled",
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure now we have the job
        event.refresh_from_db()
        self.assertTrue(PostWorkshopAction.check(event))

        # 1 new job
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjob
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

        # now change the event back to no start and no end dates
        data = {
            "slug": "2020-02-07-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "start": "",
            "end": "",
            "administrator": self.LC_org.pk,
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        self.assertContains(
            response, f"Scheduled email <code>{rqjob.job_id}</code> was removed"
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure the event doesn't pass checks anymore
        event.refresh_from_db()
        self.assertFalse(PostWorkshopAction.check(event))

        # no job
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjob
        self.assertEqual(RQJob.objects.count(), 0)


class TestEventDeletePostWorkshopAction(
    FakeRedisTestCaseMixin, SuperuserMixin, TestCase
):
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
        Tag.objects.bulk_create(
            [
                Tag(name="SWC"),
                Tag(name="DC"),
                Tag(name="LC"),
                Tag(name="automated-email"),
            ]
        )

        self.LC_org = Organization.objects.create(
            domain="librarycarpentry.org",
            fullname="Library Carpentry",
        )

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(
            action="week-after-workshop-completion",
            template=template,
        )

    def test_job_unscheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        self.client.force_login(self.admin)
        data = {
            "slug": "2020-02-07-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "start": date.today(),
            "end": date.today() + timedelta(days=2),
            "administrator": self.LC_org.pk,
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(reverse("event_add"), data, follow=True)
        self.assertContains(
            response,
            "New email (7 days past the end date of an active workshop) was scheduled",
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # new event appeared
        self.assertEqual(Event.objects.count(), 1)

        # ensure the new event passes action checks
        event = Event.objects.first()
        self.assertTrue(PostWorkshopAction.check(event))

        # 1 new jobs
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjobs
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

        # now remove the event
        response = self.client.post(
            reverse("event_delete", args=[event.slug]), follow=True
        )
        self.assertContains(
            response, f"Scheduled email <code>{rqjob.job_id}</code> was removed"
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # event is gone
        with self.assertRaises(Event.DoesNotExist):
            event.refresh_from_db()

        # no job
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjob
        self.assertEqual(RQJob.objects.count(), 0)


class TestEventCreateInstructorsHostIntroduction(TestCase):
    # It's impossible to create an InstructorsHostIntroductionAction when adding
    # a new event, because this action requires presence of 3 related tasks.
    # We cannot add tasks when creating an event.
    pass


class TestEventUpdateInstructorsHostIntroduction(
    FakeRedisTestCaseMixin, SuperuserMixin, TestCase
):
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
        Tag.objects.bulk_create(
            [
                Tag(name="SWC"),
                Tag(name="DC"),
                Tag(name="LC"),
                Tag(name="automated-email"),
            ]
        )

        self.LC_org = Organization.objects.create(
            domain="librarycarpentry.org",
            fullname="Library Carpentry",
        )

        self.instructor = Role.objects.create(name="instructor")
        self.host = Role.objects.create(name="host")

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(
            action="instructors-host-introduction",
            template=template,
        )

        self.instructor1 = Person.objects.create(
            personal="Hermione",
            family="Granger",
            email="hermione@granger.co.uk",
            username="granger_hermione",
        )
        self.instructor2 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            email="rw@magic.uk",
            username="weasley_ron",
        )
        self.host1 = Person.objects.create(
            personal="Harry",
            family="Potter",
            email="hp@magic.uk",
            username="potter_harry",
        )

    def test_job_scheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # this event shouldn't trigger action
        event = Event.objects.create(
            slug="2020-06-07-test-event",
            host=Organization.objects.first(),
            sponsor=Organization.objects.first(),
            start=None,
            end=None,
            administrator=self.LC_org,
        )
        event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        Task.objects.bulk_create(
            [
                Task(event=event, person=self.instructor1, role=self.instructor),
                Task(event=event, person=self.instructor2, role=self.instructor),
                Task(event=event, person=self.host1, role=self.host),
            ]
        )
        self.assertFalse(InstructorsHostIntroductionAction.check(event))

        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        # add start & end date and save
        self.client.force_login(self.admin)
        data = {
            "slug": "2020-06-07-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "administrator": self.LC_org.pk,
            "start": date.today() + timedelta(days=7),
            "end": date.today() + timedelta(days=9),
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        self.assertContains(
            response,
            "New email (Introduction of instructors and host (centr. org. workshop))"
            " was scheduled",
        )

        event.refresh_from_db()
        self.assertTrue(InstructorsHostIntroductionAction.check(event))

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

        # this event won't trigger an action if we created it via a view
        event = Event.objects.create(
            slug="2020-06-07-test-event",
            host=Organization.objects.first(),
            sponsor=Organization.objects.first(),
            start=None,
            end=None,
            administrator=self.LC_org,
        )
        event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        Task.objects.bulk_create(
            [
                Task(event=event, person=self.instructor1, role=self.instructor),
                Task(event=event, person=self.instructor2, role=self.instructor),
                Task(event=event, person=self.host1, role=self.host),
            ]
        )
        self.assertFalse(InstructorsHostIntroductionAction.check(event))

        # no jobs - again, due to not creating via WWW
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs - again, due to not creating via WWW
        self.assertFalse(RQJob.objects.all())

        # change event's start and end dates
        self.client.force_login(self.admin)
        data = {
            "slug": "2020-06-07-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "start": date.today() + timedelta(days=7),
            "end": date.today() + timedelta(days=9),
            "administrator": self.LC_org.pk,
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        self.assertContains(
            response,
            "New email (Introduction of instructors and host (centr. org. workshop))"
            " was scheduled",
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure now we have the job
        event.refresh_from_db()
        self.assertTrue(InstructorsHostIntroductionAction.check(event))

        # 1 new job
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjob
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

        # now change the event back to no start and no end dates
        data = {
            "slug": "2020-06-07-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "start": "",
            "end": "",
            "administrator": self.LC_org.pk,
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        self.assertContains(
            response, f"Scheduled email <code>{rqjob.job_id}</code> was removed"
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure the event doesn't pass checks anymore
        event.refresh_from_db()
        self.assertFalse(InstructorsHostIntroductionAction.check(event))

        # no job
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjob
        self.assertEqual(RQJob.objects.count(), 0)


class TestEventDeleteInstructorsHostIntroduction(
    FakeRedisTestCaseMixin, SuperuserMixin, TestCase
):
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
        Tag.objects.bulk_create(
            [
                Tag(name="SWC"),
                Tag(name="DC"),
                Tag(name="LC"),
                Tag(name="automated-email"),
            ]
        )

        self.LC_org = Organization.objects.create(
            domain="librarycarpentry.org",
            fullname="Library Carpentry",
        )

        self.instructor = Role.objects.create(name="instructor")
        self.host = Role.objects.create(name="host")

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(
            action="instructors-host-introduction",
            template=template,
        )

        self.instructor1 = Person.objects.create(
            personal="Hermione",
            family="Granger",
            email="hermione@granger.co.uk",
            username="granger_hermione",
        )
        self.instructor2 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            email="rw@magic.uk",
            username="weasley_ron",
        )
        self.host1 = Person.objects.create(
            personal="Harry",
            family="Potter",
            email="hp@magic.uk",
            username="potter_harry",
        )

    def test_job_unscheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        event = Event.objects.create(
            slug="2020-06-07-test-event",
            host=Organization.objects.first(),
            sponsor=Organization.objects.first(),
            start=None,
            end=None,
            administrator=self.LC_org,
        )
        Task.objects.bulk_create(
            [
                Task(event=event, person=self.instructor1, role=self.instructor),
                Task(event=event, person=self.instructor2, role=self.instructor),
                Task(event=event, person=self.host1, role=self.host),
            ]
        )

        self.client.force_login(self.admin)
        data = {
            "slug": "2020-06-07-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "start": date.today() + timedelta(days=7),
            "end": date.today() + timedelta(days=9),
            "administrator": self.LC_org.pk,
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )

        self.assertContains(
            response,
            "New email (Introduction of instructors and host (centr. org. workshop))"
            " was scheduled",
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure the new event passes action checks
        event.refresh_from_db()
        self.assertTrue(InstructorsHostIntroductionAction.check(event))

        # 1 new jobs
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjobs
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

        # remove related tasks
        event.task_set.all().delete()

        # now remove the event
        response = self.client.post(
            reverse("event_delete", args=[event.slug]), follow=True
        )
        self.assertContains(
            response, f"Scheduled email <code>{rqjob.job_id}</code> was removed"
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # event is gone
        with self.assertRaises(Event.DoesNotExist):
            event.refresh_from_db()

        # no job
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjob
        self.assertEqual(RQJob.objects.count(), 0)


class TestEventCreateAskForWebsite(TestCase):
    # It's impossible to create an AskForWebsiteAction when adding
    # a new event, because this action requires at least one instructor task, and
    # we cannot add tasks when creating an event.
    pass


class TestEventUpdateAskForWebsite(FakeRedisTestCaseMixin, SuperuserMixin, TestCase):
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
        Tag.objects.bulk_create([Tag(name="SWC"), Tag(name="automated-email")])

        self.instructor_role = Role.objects.create(name="instructor")
        self.host_role = Role.objects.create(name="host")
        self.host_org = Organization.objects.first()
        self.self_organized_org = Organization.objects.get(domain="self-organized")

        self.instructor = Person.objects.create(
            personal="Hermione",
            family="Granger",
            email="hermione@granger.co.uk",
            username="granger_hermione",
        )

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(action="ask-for-website", template=template)

    def test_job_scheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # this event shouldn't trigger action
        event = Event.objects.create(
            slug="2020-08-15-test-event",
            host=self.host_org,
            sponsor=self.host_org,
            administrator=self.self_organized_org,
            start=None,
            end=None,
        )
        event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        Task.objects.create(
            event=event,
            person=self.instructor,
            role=self.instructor_role,
        )
        self.assertFalse(AskForWebsiteAction.check(event))

        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        # add start & end date and save
        self.client.force_login(self.admin)
        data = {
            "slug": "2020-08-15-test-event",
            "host": self.host_org.pk,
            "sponsor": self.host_org.pk,
            "administrator": self.self_organized_org.pk,
            "start": date.today() + timedelta(days=7),
            "end": date.today() + timedelta(days=8),
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        self.assertContains(
            response,
            "New email (Website URL is missing) was scheduled",
        )

        event.refresh_from_db()
        self.assertTrue(AskForWebsiteAction.check(event))

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

        # this event won't trigger an action if we created it via a view
        event = Event.objects.create(
            slug="2020-08-15-test-event",
            host=self.host_org,
            sponsor=self.host_org,
            administrator=self.self_organized_org,
            start=None,
            end=None,
        )
        event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        Task.objects.create(
            event=event,
            person=self.instructor,
            role=self.instructor_role,
        )
        self.assertFalse(AskForWebsiteAction.check(event))

        # no jobs - again, due to not creating via WWW
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs - again, due to not creating via WWW
        self.assertFalse(RQJob.objects.all())

        # change event's start and end dates
        self.client.force_login(self.admin)
        data = {
            "slug": "2020-08-15-test-event",
            "host": self.host_org.pk,
            "sponsor": self.host_org.pk,
            "administrator": self.self_organized_org.pk,
            "start": date.today() + timedelta(days=7),
            "end": date.today() + timedelta(days=8),
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        self.assertContains(
            response,
            "New email (Website URL is missing) was scheduled",
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure now we have the job
        event.refresh_from_db()
        self.assertTrue(AskForWebsiteAction.check(event))

        # 1 new job
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjob
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

        # now change the event back to no start and no end dates
        data = {
            "slug": "2020-08-15-test-event",
            "host": self.host_org.pk,
            "sponsor": self.host_org.pk,
            "administrator": self.self_organized_org.pk,
            "start": "",
            "end": "",
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        self.assertContains(
            response, f"Scheduled email <code>{rqjob.job_id}</code> was removed"
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure the event doesn't pass checks anymore
        event.refresh_from_db()
        self.assertFalse(AskForWebsiteAction.check(event))

        # no job
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjob
        self.assertEqual(RQJob.objects.count(), 0)


class TestEventDeleteAskForWebsite(FakeRedisTestCaseMixin, SuperuserMixin, TestCase):
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
        Tag.objects.bulk_create([Tag(name="SWC"), Tag(name="automated-email")])

        self.instructor_role = Role.objects.create(name="instructor")
        self.host_role = Role.objects.create(name="host")
        self.host_org = Organization.objects.first()
        self.self_organized_org = Organization.objects.get(domain="self-organized")

        self.instructor = Person.objects.create(
            personal="Hermione",
            family="Granger",
            email="hermione@granger.co.uk",
            username="granger_hermione",
        )

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(action="ask-for-website", template=template)

    def test_job_unscheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # this event won't trigger an action if we created it via a view
        event = Event.objects.create(
            slug="2020-08-15-test-event",
            host=self.host_org,
            sponsor=self.host_org,
            administrator=self.self_organized_org,
            start=None,
            end=None,
        )
        event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        Task.objects.create(
            event=event,
            person=self.instructor,
            role=self.instructor_role,
        )
        self.assertFalse(AskForWebsiteAction.check(event))

        # no jobs - again, due to not creating via WWW
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs - again, due to not creating via WWW
        self.assertFalse(RQJob.objects.all())

        # change event's start and end dates
        self.client.force_login(self.admin)
        data = {
            "slug": "2020-08-15-test-event",
            "host": self.host_org.pk,
            "sponsor": self.host_org.pk,
            "administrator": self.self_organized_org.pk,
            "start": date.today() + timedelta(days=7),
            "end": date.today() + timedelta(days=8),
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        self.assertContains(
            response,
            "New email (Website URL is missing) was scheduled",
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure now we have the job
        event.refresh_from_db()
        self.assertTrue(AskForWebsiteAction.check(event))

        # 1 new job
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjob
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

        # remove related tasks
        event.task_set.all().delete()

        # now remove the event
        response = self.client.post(
            reverse("event_delete", args=[event.slug]), follow=True
        )
        self.assertContains(
            response, f"Scheduled email <code>{rqjob.job_id}</code> was removed"
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # event is gone
        with self.assertRaises(Event.DoesNotExist):
            event.refresh_from_db()

        # no job
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjob
        self.assertEqual(RQJob.objects.count(), 0)


class TestEventCreateRecruitHelpers(TestCase):
    # It's impossible to create a RecruitHelpersAction when adding
    # a new event, because this action requires at least one instructor or host task,
    # and we cannot add tasks when creating an event.
    pass


class TestEventUpdateRecruitHelpers(FakeRedisTestCaseMixin, SuperuserMixin, TestCase):
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
        Tag.objects.bulk_create([Tag(name="SWC"), Tag(name="automated-email")])

        self.host_role = Role.objects.create(name="host")
        self.instructor_role = Role.objects.create(name="instructor")
        self.helper_role = Role.objects.create(name="helper")
        self.host_org = Organization.objects.create(
            domain="librarycarpentry.org",
            fullname="Library Carpentry",
        )

        self.instructor = Person.objects.create(
            personal="Hermione",
            family="Granger",
            email="hermione@granger.co.uk",
            username="granger_hermione",
        )

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(action="recruit-helpers", template=template)

    def test_job_scheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # this event shouldn't trigger action
        event = Event.objects.create(
            slug="2020-08-18-test-event",
            host=self.host_org,
            sponsor=self.host_org,
            administrator=self.host_org,
            start=None,
            end=None,
        )
        event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        Task.objects.create(
            event=event,
            person=self.instructor,
            role=self.instructor_role,
        )
        self.assertFalse(RecruitHelpersAction.check(event))

        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        # add start & end date and save
        self.client.force_login(self.admin)
        data = {
            "slug": "2020-08-18-test-event",
            "host": self.host_org.pk,
            "sponsor": self.host_org.pk,
            "administrator": self.host_org.pk,
            "start": date.today() + timedelta(days=40),
            "end": date.today() + timedelta(days=41),
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
            "url": "http://example.org",
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        self.assertContains(
            response,
            "New email (Recruit helpers) was scheduled",
        )

        event.refresh_from_db()
        self.assertTrue(RecruitHelpersAction.check(event))

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

        # this event won't trigger an action if we created it via a view
        event = Event.objects.create(
            slug="2020-08-18-test-event",
            host=self.host_org,
            sponsor=self.host_org,
            administrator=self.host_org,
            start=None,
            end=None,
        )
        event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        Task.objects.create(
            event=event,
            person=self.instructor,
            role=self.instructor_role,
        )
        self.assertFalse(RecruitHelpersAction.check(event))

        # no jobs - again, due to not creating via WWW
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs - again, due to not creating via WWW
        self.assertFalse(RQJob.objects.all())

        # change event's start and end dates
        self.client.force_login(self.admin)
        data = {
            "slug": "2020-08-18-test-event",
            "host": self.host_org.pk,
            "sponsor": self.host_org.pk,
            "administrator": self.host_org.pk,
            "start": date.today() + timedelta(days=40),
            "end": date.today() + timedelta(days=41),
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
            "url": "http://example.org",
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        self.assertContains(
            response,
            "New email (Recruit helpers) was scheduled",
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure now we have the job
        event.refresh_from_db()
        self.assertTrue(RecruitHelpersAction.check(event))

        # 1 new job
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjob
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

        # now change the event back to no start and no end dates
        data = {
            "slug": "2020-08-18-test-event",
            "host": self.host_org.pk,
            "sponsor": self.host_org.pk,
            "administrator": self.host_org.pk,
            "start": "",
            "end": "",
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
            "url": "http://example.org",
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        self.assertContains(
            response, f"Scheduled email <code>{rqjob.job_id}</code> was removed"
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure the event doesn't pass checks anymore
        event.refresh_from_db()
        self.assertFalse(RecruitHelpersAction.check(event))

        # no job
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjob
        self.assertEqual(RQJob.objects.count(), 0)


class TestEventDeleteRecruitHelpers(FakeRedisTestCaseMixin, SuperuserMixin, TestCase):
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
        Tag.objects.bulk_create([Tag(name="SWC"), Tag(name="automated-email")])

        self.host_role = Role.objects.create(name="host")
        self.instructor_role = Role.objects.create(name="instructor")
        self.helper_role = Role.objects.create(name="helper")
        self.host_org = Organization.objects.create(
            domain="librarycarpentry.org",
            fullname="Library Carpentry",
        )

        self.instructor = Person.objects.create(
            personal="Hermione",
            family="Granger",
            email="hermione@granger.co.uk",
            username="granger_hermione",
        )

        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(action="recruit-helpers", template=template)

    def test_job_unscheduled(self):
        self._setUpSuperuser()
        self._prepare_data()

        # this event won't trigger an action if we created it via a view
        event = Event.objects.create(
            slug="2020-08-18-test-event",
            host=self.host_org,
            sponsor=self.host_org,
            administrator=self.host_org,
            start=None,
            end=None,
        )
        event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        Task.objects.create(
            event=event,
            person=self.instructor,
            role=self.instructor_role,
        )
        self.assertFalse(RecruitHelpersAction.check(event))

        # no jobs - again, due to not creating via WWW
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs - again, due to not creating via WWW
        self.assertFalse(RQJob.objects.all())

        # change event's start and end dates
        self.client.force_login(self.admin)
        data = {
            "slug": "2020-08-18-test-event",
            "host": self.host_org.pk,
            "sponsor": self.host_org.pk,
            "administrator": self.host_org.pk,
            "start": date.today() + timedelta(days=40),
            "end": date.today() + timedelta(days=41),
            "tags": Tag.objects.filter(name__in=["LC", "automated-email"]).values_list(
                "pk", flat=True
            ),
            "url": "http://example.org",
        }
        response = self.client.post(
            reverse("event_edit", args=[event.slug]), data, follow=True
        )
        self.assertContains(
            response,
            "New email (Recruit helpers) was scheduled",
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # ensure now we have the job
        event.refresh_from_db()
        self.assertTrue(RecruitHelpersAction.check(event))

        # 1 new job
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjob
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

        # remove related tasks
        event.task_set.all().delete()

        # now remove the event
        response = self.client.post(
            reverse("event_delete", args=[event.slug]), follow=True
        )
        self.assertContains(
            response, f"Scheduled email <code>{rqjob.job_id}</code> was removed"
        )
        # with open('test.html', 'w', encoding='utf-8') as f:
        #     f.write(response.content.decode('utf-8'))

        # event is gone
        with self.assertRaises(Event.DoesNotExist):
            event.refresh_from_db()

        # no job
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjob
        self.assertEqual(RQJob.objects.count(), 0)
