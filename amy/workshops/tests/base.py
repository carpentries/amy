import contextlib
import datetime
import itertools
import sys

from django.contrib.auth.models import Group, Permission
from django.contrib.sites.models import Site
from django_webtest import WebTest
import webtest.forms

from workshops.models import (
    Airport,
    Award,
    Badge,
    Event,
    Lesson,
    Person,
    Qualification,
    Organization,
    Role,
    Tag,
    Language,
)
from workshops.util import universal_date_format


@contextlib.contextmanager
def dummy_subTest():
    yield


class DummySubTestWhenTestsLaunchedInParallelMixin:
    def subTest(self, *args, **kwargs):
        # If you launch tests in parallel, subTest is not supported yet. To
        # fix that, we provide a dummy subTest implementation in that case.
        if '--parallel' in sys.argv:
            return dummy_subTest()
        else:
            return super().subTest(*args, **kwargs)


class TestBase(DummySubTestWhenTestsLaunchedInParallelMixin,
               WebTest):  # Support for functional tests (django-webtest)
    '''Base class for AMY test cases.'''

    def setUp(self):
        '''Create standard objects.'''

        # self.clear_sites_cache()
        self._setUpOrganizations()
        self._setUpAirports()
        self._setUpLessons()
        self._setUpBadges()
        self._setUpInstructors()
        self._setUpNonInstructors()
        self._setUpPermissions()

        from django.conf import settings
        Site.objects.clear_cache()
        Site.objects.get_or_create(pk=settings.SITE_ID,
                                   defaults=dict(domain='amy.carpentries.org',
                                                 name='AMY server'))

    def clear_sites_cache(self):
        # we need to clear Sites' cache, because after post_migration signal,
        # there's some junk in the cache that prevents from adding comments
        # (the site in CACHE is not a real Site)
        Site.objects.clear_cache()

    def _setUpLessons(self):
        '''Set up lesson objects.'''

        # we have some lessons in the database because of the migration
        # '0012_auto_20150612_0807.py'
        self.git, _ = Lesson.objects.get_or_create(name='swc/git')
        self.sql, _ = Lesson.objects.get_or_create(name='dc/sql')
        self.matlab, _ = Lesson.objects.get_or_create(name='swc/matlab')
        self.r, _ = Lesson.objects.get_or_create(name='swc/r')

    def _setUpOrganizations(self):
        '''Set up organization objects.'''

        self.org_alpha = Organization.objects.create(
            domain='alpha.edu', fullname='Alpha Organization',
            country='Azerbaijan')

        self.org_beta = Organization.objects.create(
            domain='beta.com', fullname='Beta Organization', country='Brazil')

    def _setUpAirports(self):
        '''Set up airport objects.'''

        self.airport_0_10 = Airport.objects.create(
            iata='ZZZ', fullname='Airport 0x10',
            latitude=0.0, longitude=10.0,
        )
        self.airport_0_0 = Airport.objects.create(
            iata='AAA', fullname='Airport 0x0', country='AL',  # AL for Albania
            latitude=0.0, longitude=0.0,
        )
        self.airport_0_50 = Airport.objects.create(
            iata='BBB', fullname='Airport 0x50',
            country='BG',  # BG for Bulgaria
            latitude=0.0, longitude=50.0,
        )
        self.airport_50_100 = Airport.objects.create(
            iata='CCC', fullname='Airport 50x100',
            country='CM',  # CM for Cameroon
            latitude=50.0, longitude=100.0,
        )
        self.airport_55_105 = Airport.objects.create(
            iata='DDD', fullname='Airport 55x105',
            country='CM',
            latitude=55.0, longitude=105.0)

    def _setUpLanguages(self):
        '''Set up language objects.'''

        self.english, _ = Language.objects.get_or_create(
            name='English',
        )
        self.french, _ = Language.objects.get_or_create(
            name='French',
        )
        self.latin, _ = Language.objects.get_or_create(
            name='Latin',
        )

    def _setUpBadges(self):
        '''Set up badge objects.'''

        self.swc_instructor, _ = Badge.objects.get_or_create(
            name='swc-instructor',
            defaults=dict(title='Software Carpentry Instructor',
                          criteria='Worked hard for this'))
        self.dc_instructor, _ = Badge.objects.get_or_create(
            name='dc-instructor',
            defaults=dict(title='Data Carpentry Instructor',
                          criteria='Worked hard for this'))
        # lc-instructor is provided via a migration
        self.lc_instructor = Badge.objects.get(name='lc-instructor')

    def _setUpInstructors(self):
        '''Set up person objects representing instructors.'''

        self.hermione = Person.objects.create(
            personal='Hermione', family='Granger',
            email='hermione@granger.co.uk', gender='F', may_contact=True,
            airport=self.airport_0_0, github='herself', twitter='herself',
            url='http://hermione.org', username="granger_hermione",
            country='GB')

        # Hermione is additionally a qualified Data Carpentry instructor
        Award.objects.create(person=self.hermione,
                             badge=self.swc_instructor,
                             awarded=datetime.date(2014, 1, 1))
        Award.objects.create(person=self.hermione,
                             badge=self.dc_instructor,
                             awarded=datetime.date(2014, 1, 1))
        Award.objects.create(person=self.hermione,
                             badge=self.lc_instructor,
                             awarded=datetime.date(2018, 12, 25))
        Qualification.objects.create(person=self.hermione, lesson=self.git)
        Qualification.objects.create(person=self.hermione, lesson=self.sql)

        self.harry = Person.objects.create(
            personal='Harry', family='Potter',
            email='harry@hogwarts.edu', gender='M', may_contact=True,
            airport=self.airport_0_50, github='hpotter', twitter=None,
            username="potter_harry",
            country='GB')

        # Harry is additionally a qualified Data Carpentry instructor
        Award.objects.create(person=self.harry,
                             badge=self.swc_instructor,
                             awarded=datetime.date(2014, 5, 5))
        Award.objects.create(person=self.harry,
                             badge=self.dc_instructor,
                             awarded=datetime.date(2014, 5, 5))
        Qualification.objects.create(person=self.harry, lesson=self.sql)

        self.ron = Person.objects.create(
            personal='Ron', family='Weasley',
            email='rweasley@ministry.gov.uk', gender='M', may_contact=False,
            airport=self.airport_50_100, github=None, twitter=None,
            url='http://geocities.com/ron_weas', username="weasley_ron",
            country='GB')

        Award.objects.create(person=self.ron,
                             badge=self.swc_instructor,
                             awarded=datetime.date(2014, 11, 11))
        Qualification.objects.create(person=self.ron, lesson=self.git)

    def _setUpNonInstructors(self):
        '''Set up person objects representing non-instructors.'''

        self.spiderman = Person.objects.create(
            personal='Peter', middle='Q.', family='Parker',
            email='peter@webslinger.net', gender='O', may_contact=True,
            username="spiderman", airport=self.airport_55_105,
            country='US')

        self.ironman = Person.objects.create(
            personal='Tony', family='Stark', email='me@stark.com',
            gender='M', may_contact=True, username="ironman",
            airport=self.airport_50_100,
            country='US')

        self.blackwidow = Person.objects.create(
            personal='Natasha', family='Romanova', email=None,
            gender='F', may_contact=False, username="blackwidow",
            airport=self.airport_0_50,
            country='RU')

    def _setUpUsersAndLogin(self):
        """Set up one account for administrator that can log into the website.

        Log this user in.
        """
        password = "admin"
        self.admin = Person.objects.create_superuser(
                username="admin", personal="Super", family="User",
                email="sudo@example.org", password=password)
        self.admin.data_privacy_agreement = True
        self.admin.save()

        # log user in
        # this user will be authenticated for all self.client requests
        return self.client.login(username=self.admin.username,
                                 password=password)

    def _setUpPermissions(self):
        '''Set up permission objects for consistent form selection.'''
        badge_admin = Group.objects.create(name='Badge Admin')
        badge_admin.permissions.add(*Permission.objects.filter(
            codename__endswith='_badge'))
        try:
            add_badge = Permission.objects.get(codename='add_badge')
        except:
            print([p.codename for p in Permission.objects.all()])
            raise
        self.ironman.groups.add(badge_admin)
        self.ironman.user_permissions.add(add_badge)
        self.ron.groups.add(badge_admin)
        self.ron.user_permissions.add(add_badge)
        self.spiderman.groups.add(badge_admin)
        self.spiderman.user_permissions.add(add_badge)

    def _setUpTags(self):
        """Set up tags (the same as in production database, minus some added
        via migrations)."""
        Tag.objects.bulk_create([
            Tag(name='TTT', details=''),
            Tag(name='WiSE', details=''),
            Tag(name='LC', details=''),
            Tag(name='DC', details=''),
            Tag(name='SWC', details=''),
        ])

    def _setUpEvents(self):
        '''Set up a bunch of events and record some statistics.'''

        today = datetime.date.today()

        # Create a test host
        test_host = Organization.objects.create(domain='example.com',
                                        fullname='Test Organization')

        # Create one new published event for each day in the next 10 days.
        for t in range(1, 11):
            event_start = today + datetime.timedelta(days=t)
            date_string = universal_date_format(event_start)
            slug = '{0}-upcoming'.format(date_string)
            url = 'http://example.org/' + ('{0}'.format(t) * 20)
            e = Event.objects.create(
                start=event_start, slug=slug,
                host=test_host, admin_fee=100,
                url=url, invoice_status='not-invoiced',
                country='US', venue='School', address='Overthere',
                latitude=1, longitude=2)

        # Create one new event for each day from 10 days ago to
        # 3 days ago, half invoiced
        invoice = itertools.cycle(['invoiced', 'not-invoiced'])
        for t in range(3, 11):
            event_start = today + datetime.timedelta(days=-t)
            date_string = universal_date_format(event_start)
            Event.objects.create(start=event_start,
                                 slug='{0}-past'.format(date_string),
                                 host=test_host,
                                 admin_fee=100,
                                 invoice_status=next(invoice))

        # create a past event that has no admin fee specified, yet it needs
        # invoice
        event_start = today + datetime.timedelta(days=-4)
        Event.objects.create(
            start=event_start, end=today + datetime.timedelta(days=-1),
            slug='{}-past-uninvoiced'.format(
                universal_date_format(event_start)
            ),
            host=test_host, admin_fee=None, invoice_status='not-invoiced',
        )

        # Create an event that started yesterday and ends tomorrow
        # with no fee, and without specifying whether they've been
        # invoiced.
        event_start = today + datetime.timedelta(days=-1)
        event_end = today + datetime.timedelta(days=1)
        Event.objects.create(
            start=event_start, end=event_end, slug='ends-tomorrow-ongoing',
            host=test_host, admin_fee=0,
            url='http://example.org/ends-tomorrow-ongoing',
            country='US', venue='School', address='Overthere',
            latitude=1, longitude=2)

        # Create an event that ends today with no fee, and without
        # specifying whether the fee has been invoiced.
        event_start = today + datetime.timedelta(days=-1)
        event_end = today
        Event.objects.create(
            start=event_start, end=event_end, slug='ends-today-ongoing',
            host=test_host, admin_fee=0,
            url='http://example.org/ends-today-ongoing',
            country='US', venue='School', address='Overthere',
            latitude=1, longitude=2)

        # Create an event that starts today with a fee, and without
        # specifying whether the fee has been invoiced.
        event_start = today
        event_end = today + datetime.timedelta(days=1)
        Event.objects.create(start=event_start,
                             end=event_end,
                             slug='starts-today-ongoing',
                             host=test_host,
                             admin_fee=100)

        # create a full-blown event that got cancelled
        e = Event.objects.create(start=event_start, end=event_end,
                                 slug='starts-today-cancelled',
                                 url='http://example.org/cancelled-event',
                                 latitude=-10.0, longitude=10.0,
                                 country='US', venue='University',
                                 address='Phenomenal Street',
                                 host=test_host)
        tags = Tag.objects.filter(name__in=['SWC', 'cancelled'])
        e.tags.set(tags)

        # Record some statistics about events.
        self.num_uninvoiced_events = 0
        self.num_upcoming = 0
        for e in Event.objects.all():
            e.is_past_event = e.start < today and (e.end is None or e.end < today)
            if e.invoice_status == 'not-invoiced' and e.is_past_event:
                self.num_uninvoiced_events += 1
            if e.url and (e.start > today):
                self.num_upcoming += 1

    def _setUpRoles(self):
        """Before #626, we don't have a migration that introduces roles that
        are currently in the database.  This is an auxiliary method for adding
        them to the tests, should one need them."""
        Role.objects.bulk_create([
            Role(name='helper', verbose_name='Helper'),
            Role(name='instructor', verbose_name='Instructor'),
            Role(name='host', verbose_name='Host'),
            Role(name='learner', verbose_name='Learner'),
            Role(name='organizer', verbose_name='Organizer'),
            Role(name='tutor', verbose_name='Tutor'),
        ])

    def saveResponse(self, response, filename='error.html'):
        content = response.content.decode('utf-8')
        with open(filename, 'w') as f:
            f.write(content)

    # Web-test helpers
    def assertSelected(self, field, expected):
        if not isinstance(field, webtest.forms.Select):
            raise TypeError

        expected_value = field._get_value_for_text(expected)
        got_value = field.value

        # field.options is a list of (value, selected?, verbose name) triples
        selected = [o[2] for o in field.options if o[1]]

        self.assertEqual(
            expected_value, got_value,
            msg='Expected "{}" to be selected '
                'while {} is/are selected.'.format(expected, selected))

    def passCaptcha(self, data_dictionary):
        """Extends provided `data_dictionary` with RECAPTCHA pass data."""
        data_dictionary.update(
            {'g-recaptcha-response': 'PASSED'}  # to auto-pass RECAPTCHA
        )


class FormTestHelper:
    def _test_field_other(self, Form, first_name, other_name, valid_first,
                          valid_other, empty_first='', empty_other='',
                          first_when_other="", blank=False):
        """Universal way of testing field `name` and it's "_other" counterpart
        `other_name`.

        4 test scenarios are implemented:
        1) no data in either field - first field throws error if required by
           `blank`
        2) valid entry in first, requiring no input in the other
        3) valid entry in second, requiring no input in the first one
        4) both entries filled, error in the second"""

        # 1: data required
        data = {
            first_name: empty_first,
            other_name: empty_other,
        }
        form = Form(data)
        if blank:
            self.assertNotIn(first_name, form.errors)
            self.assertNotIn(other_name, form.errors)
        else:
            self.assertIn(first_name, form.errors)
            self.assertNotIn(other_name, form.errors)

        # 2: valid entry (original field only)
        data = {
            first_name: valid_first,
            other_name: empty_other,
        }
        form = Form(data)
        self.assertNotIn(first_name, form.errors)
        self.assertNotIn(other_name, form.errors)

        # 3: valid entry ("other" field only)
        data = {
            first_name: first_when_other,
            other_name: valid_other,
        }
        form = Form(data)
        self.assertNotIn(first_name, form.errors)
        self.assertNotIn(other_name, form.errors)

        # 4: invalid entry, data in "other" is not needed
        data = {
            first_name: valid_first,
            other_name: valid_other,
        }
        form = Form(data)
        self.assertIn(first_name, form.errors)
        self.assertNotIn(other_name, form.errors)
