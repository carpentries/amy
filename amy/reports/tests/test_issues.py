from datetime import timedelta, date

from django.urls import reverse

from workshops.tests.base import TestBase
from workshops.models import Event, Organization, Role, Person, Tag


class TestIssuesViews(TestBase):
    def setUp(self):
        super()._setUpUsersAndLogin()
        super()._setUpRoles()
        super()._setUpTags()

        self.url = reverse('workshop_issues')
        self.today = date.today()
        oneday = timedelta(days=1)
        self.weekago = self.today - 7 * oneday
        self.yesterday = self.today - oneday
        self.tomorrow = self.today + oneday
        self.instructor_role = Role.objects.get(name='instructor')

    def test_workshop_issues_past(self):
        """Test if workshop issues collects events from past only."""
        past = Event.objects.create(
            slug='event-in-past', start=self.yesterday,
            host=Organization.objects.first())
        future = Event.objects.create(
            slug='event-in-future', start=self.tomorrow,
            host=Organization.objects.first())

        rv = self.client.get(self.url)
        self.assertIn(past, rv.context['events'])
        self.assertNotIn(future, rv.context['events'])

    def test_workshop_issues_active(self):
        """Test if workshop issues collects active events only."""
        inactive = Event.objects.create(
            slug='inactive-event', start=self.yesterday,
            completed=True, host=Organization.objects.first())
        active = Event.objects.create(
            slug='active-event', start=self.yesterday,
            completed=False, host=Organization.objects.first())

        rv = self.client.get(self.url)
        self.assertNotIn(inactive, rv.context['events'])
        self.assertIn(active, rv.context['events'])

    def test_workshop_issues_no_attendance(self):
        """Test if workshop issues collects events without attendance
        figures."""
        attendance = Event.objects.create(
            slug='event-with-attendance',
            start=self.weekago, end=self.yesterday,
            manual_attendance=36, host=Organization.objects.first(),
            country='US', address='A', venue='B', latitude=89, longitude=179)
        attendance.task_set.create(person=Person.objects.first(),
                                   role=self.instructor_role)
        no_attendance = Event.objects.create(
            slug='event-with-no-attendance',
            start=self.weekago, end=self.yesterday,
            manual_attendance=0, host=Organization.objects.first(),
            country='US', address='A', venue='B', latitude=89, longitude=179)
        no_attendance.task_set.create(person=Person.objects.first(),
                                      role=self.instructor_role)
        no_attendance_unresponsive = Event.objects.create(
            slug='unresponsive-event-with-no-attendance',
            start=self.weekago, end=self.yesterday,
            manual_attendance=0, host=Organization.objects.first(),
            country='US', address='A', venue='B', latitude=89, longitude=179)
        no_attendance_unresponsive.task_set.create(
            person=Person.objects.first(), role=self.instructor_role)
        no_attendance_unresponsive.tags.add(
            Tag.objects.get(name='unresponsive'))

        rv = self.client.get(self.url)
        self.assertNotIn(attendance, rv.context['events'])
        self.assertNotIn(no_attendance_unresponsive, rv.context['events'])
        self.assertIn(no_attendance, rv.context['events'])

    def test_workshop_issues_no_location(self):
        """Test if workshop issues collects events without location."""
        location = Event.objects.create(
            slug='event-with-location',
            start=self.weekago, end=self.yesterday,
            manual_attendance=36, host=Organization.objects.first(),
            country='US', address='A', venue='B', latitude=89, longitude=179)
        location.task_set.create(person=Person.objects.first(),
                                 role=self.instructor_role)
        no_location = Event.objects.create(
            slug='event-with-no-location',
            start=self.weekago, end=self.yesterday,
            manual_attendance=36, host=Organization.objects.first(),
            country='US', address='', venue='B', latitude=89, longitude=179)
        no_location.task_set.create(person=Person.objects.first(),
                                    role=self.instructor_role)

        rv = self.client.get(self.url)
        self.assertNotIn(location, rv.context['events'])
        self.assertIn(no_location, rv.context['events'])

    def test_workshop_issues_wrong_dates(self):
        """Test if workshop issues collects events with invalid dates."""
        okay = Event.objects.create(
            slug='event-with-okay-dates',
            start=self.weekago, end=self.yesterday,
            manual_attendance=36, host=Organization.objects.first(),
            country='US', address='A', venue='B', latitude=89, longitude=179)
        okay.task_set.create(person=Person.objects.first(),
                             role=self.instructor_role)
        invalid_dates = Event.objects.create(
            slug='event-with-invalid-dates',
            start=self.yesterday, end=self.weekago,
            manual_attendance=36, host=Organization.objects.first(),
            country='US', address='A', venue='B', latitude=89, longitude=179)
        invalid_dates.task_set.create(person=Person.objects.first(),
                                      role=self.instructor_role)

        rv = self.client.get(self.url)
        self.assertNotIn(okay, rv.context['events'])
        self.assertIn(invalid_dates, rv.context['events'])

    def test_workshop_issues_no_instructors(self):
        """Test if workshop issues collects events without instructors."""
        instructor = Event.objects.create(
            slug='event-with-instructor',
            start=self.weekago, end=self.yesterday,
            manual_attendance=36, host=Organization.objects.first(),
            country='US', address='A', venue='B', latitude=89, longitude=179)
        instructor.task_set.create(person=Person.objects.first(),
                                   role=self.instructor_role)
        no_instructors = Event.objects.create(
            slug='event-with-no-instructors',
            start=self.weekago, end=self.yesterday,
            manual_attendance=36, host=Organization.objects.first(),
            country='US', address='A', venue='B', latitude=89, longitude=179)

        rv = self.client.get(self.url)
        self.assertNotIn(instructor, rv.context['events'])
        self.assertIn(no_instructors, rv.context['events'])
