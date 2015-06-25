import cgi
import traceback
import datetime
import os
import re
import itertools
import xml.etree.ElementTree as ET

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.urlresolvers import reverse
from django.test import TestCase

from ..models import \
    Airport, \
    Award, \
    Badge, \
    Event, \
    Person, \
    Qualification, \
    Site, \
    Skill


class TestBase(TestCase):
    '''Base class for AMY test cases.'''

    ERR_DIR = 'htmlerror' # where to save error HTML files

    def setUp(self):
        '''Create standard objects.'''

        self._setUpSites()
        self._setUpAirports()
        self._setUpSkills()
        self._setUpBadges()
        self._setUpInstructors()
        self._setUpNonInstructors()
        self._setUpPermissions()

    def _setUpSkills(self):
        '''Set up skill objects.'''

        self.git = Skill.objects.create(name='Git')
        self.sql = Skill.objects.create(name='SQL')

    def _setUpSites(self):
        '''Set up site objects.'''

        self.site_alpha = Site.objects.create(domain='alpha.edu',
                                              fullname='Alpha Site',
                                              country='Azerbaijan',
                                              notes='')

        self.site_beta = Site.objects.create(domain='beta.com',
                                             fullname='Beta Site',
                                             country='Brazil',
                                             notes='Notes\nabout\nBrazil\n')

    def _setUpAirports(self):
        '''Set up airport objects.'''

        self.airport_0_0 = Airport.objects.create(iata='AAA', fullname='Airport 0x0', country='Albania',
                                                  latitude=0.0, longitude=0.0)
        self.airport_0_50 = Airport.objects.create(iata='BBB', fullname='Airport 0x50', country='Bulgaria',
                                                   latitude=0.0, longitude=50.0)
        self.airport_50_100 = Airport.objects.create(iata='CCC', fullname='Airport 50x100', country='Cameroon',
                                                     latitude=50.0, longitude=100.0)
        self.airport_55_105 = Airport.objects.create(iata='DDD', fullname='Airport 55x105', country='Cameroon',
                                                     latitude=55.0, longitude=105.0)

    def _setUpBadges(self):
        '''Set up badge objects.'''

        self.instructor = Badge.objects.create(name='instructor',
                                               title='Software Carpentry Instructor',
                                               criteria='Worked hard for this')

    def _setUpInstructors(self):
        '''Set up person objects representing instructors.'''

        self.hermione = Person.objects.create(
            personal='Hermione', middle=None, family='Granger',
            email='hermione@granger.co.uk', gender='F', may_contact=True,
            airport=self.airport_0_0, github='herself', twitter='herself',
            url='http://hermione.org', username="granger.h")

        Award.objects.create(person=self.hermione,
                             badge=self.instructor,
                             awarded=datetime.date(2014, 1, 1))
        Qualification.objects.create(person=self.hermione, skill=self.git)
        Qualification.objects.create(person=self.hermione, skill=self.sql)

        self.harry = Person.objects.create(
            personal='Harry', middle=None, family='Potter',
            email='harry@hogwarts.edu', gender='M', may_contact=True,
            airport=self.airport_0_50, github='hpotter', twitter=None,
            url=None, username="potter.h")

        Award.objects.create(person=self.harry,
                             badge=self.instructor,
                             awarded=datetime.date(2014, 5, 5))
        Qualification.objects.create(person=self.harry, skill=self.sql)

        self.ron = Person.objects.create(
            personal='Ron', middle=None, family='Weasley',
            email='rweasley@ministry.gov.uk', gender='M', may_contact=False,
            airport=self.airport_50_100, github=None, twitter=None,
            url='http://geocities.com/ron_weas', username="weasley.ron")

        Award.objects.create(person=self.ron,
                             badge=self.instructor,
                             awarded=datetime.date(2014, 11, 11))
        Qualification.objects.create(person=self.ron, skill=self.git)

    def _setUpNonInstructors(self):
        '''Set up person objects representing non-instructors.'''

        self.spiderman = Person.objects.create(
            personal='Peter', middle='Q.', family='Parker',
            email='peter@webslinger.net', gender='O', may_contact=True,
            username="spiderman")

        self.ironman = Person.objects.create(
            personal='Tony', middle=None, family='Stark', email='me@stark.com',
            gender=None, may_contact=True, username="ironman")

        self.blackwidow = Person.objects.create(
            personal='Natasha', middle=None, family='Romanova', email=None,
            gender='F', may_contact=False, username="blackwidow")

    def _setUpUsersAndLogin(self):
        """Set up one account for administrator that can log into the website.

        Log this user in.
        """
        password = "admin"
        self.admin = Person.objects.create_superuser(
                username="admin", personal="Super", family="User",
                email="sudo@example.org", password=password)

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

    def _setUpEvents(self):
        '''Set up a bunch of events and record some statistics.'''

        today = datetime.date.today()

        # Create a test site
        test_site = Site.objects.create(domain='example.com',
                                        fullname='Test Site')

        # Create one new event for each day in the next 10 days,
        # half with URLs.
        add_url = True
        for t in range(1, 11):
            event_start = today + datetime.timedelta(days=t)
            date_string = event_start.strftime('%Y-%m-%d')
            slug = '{0}-upcoming'.format(date_string)
            if add_url:
                url = 'http://' + ('{0}'.format(t) * 20)
            else:
                url = None
            add_url = not add_url
            e = Event.objects.create(start=event_start,
                                     slug=slug,
                                     site=test_site,
                                     admin_fee=100,
                                     invoiced=False,
                                     url=url)

        # Create one new event for each day from 10 days ago to
        # 3 days ago, half invoiced
        invoiced = True
        for t in range(3, 11):
            event_start = today + datetime.timedelta(days=-t)
            date_string = event_start.strftime('%Y-%m-%d')
            Event.objects.create(start=event_start,
                                 slug='{0}-past'.format(date_string),
                                 site=test_site,
                                 admin_fee=100,
                                 invoiced=invoiced)
            invoiced = not invoiced

        # Create an event that started yesterday and ends tomorrow
        # with no fee, and without specifying whether they've been
        # invoiced.
        event_start = today + datetime.timedelta(days=-1)
        event_end = today + datetime.timedelta(days=1)
        Event.objects.create(start=event_start,
                             end=event_end,
                             slug='ends_tomorrow',
                             site=test_site,
                             admin_fee=0)

        # Create an event that ends today with no fee, and without
        # specifying whether the fee has been invoiced.
        event_start = today + datetime.timedelta(days=-1)
        event_end = today
        Event.objects.create(start=event_start,
                             end=event_end,
                             slug='ends_today',
                             site=test_site,
                             admin_fee=0)

        # Create an event that starts today with a fee, and without
        # specifying whether the fee has been invoiced.
        event_start = today
        event_end = today + datetime.timedelta(days=1)
        Event.objects.create(start=event_start,
                             end=event_end,
                             slug='starts_today',
                             site=test_site,
                             admin_fee=100)

        # Record some statistics about events.
        self.num_uninvoiced_events = 0
        self.num_upcoming = 0
        for e in Event.objects.all():
            if (e.admin_fee > 0) and (not e.invoiced) and (e.start < today):
                self.num_uninvoiced_events += 1
            if e.url and (e.start > today):
                self.num_upcoming += 1


    def _parse(self, response, save_to=None):
        """
        Parse the HTML page returned by the server.
        Must remove the DOCTYPE to avoid confusing Python's XML parser.
        Must also remove the namespacing, or use long-form names for elements.
        If save_to is a path, save a copy of the content to that file
        for debugging.
        """
        _, params = cgi.parse_header(response['content-type'])
        charset = params['charset']
        content = response.content.decode(charset)

        # Save the raw HTML if explicitly asked to (during debugging).
        if save_to:
            with open(save_to, 'w') as writer:
                writer.write(content)

        # Report unfilled tags.
        STRING_IF_INVALID = \
            settings.TEMPLATES[0]['OPTIONS']['string_if_invalid']
        if STRING_IF_INVALID in content:
            self._save_html(content)
            lines = content.split('\n')
            hits = [x for x in enumerate(lines) if STRING_IF_INVALID in x[1]]
            msg = '"{0}" found in HTML page:\n'.format(STRING_IF_INVALID)
            assert not hits, msg + '\n'.join(['{0}: "{1}"'.format(h[0], h[1].rstrip())
                                              for h in hits])

        # Make the content safe to parse.
        content = re.sub('<!DOCTYPE [^>]*>', '', content)
        content = re.sub('<html[^>]*>', '<html>', content)
        content = content.replace('&nbsp;', ' ')

        # Parse if we can.
        try:
            doc = ET.XML(content)
            return doc
        # ...and save in a uniquely-named file if we can't.
        except ET.ParseError as e:
            self._save_html(content)
            assert False, 'HTML parsing failed: {0}'.format(str(e))

    def _check_status_code_and_parse(self, response, expected, ignore_errors=False):
        '''Check the status code, then parse if it is OK.'''
        assert response.status_code == expected, \
            'Got status code {0}, expected {1}'.format(response.status_code, expected)
        doc = self._parse(response=response)
        if not ignore_errors:
            errors = self._collect_errors(doc)
            if errors:
                caller = self._get_test_name_from_stack()
                assert False, 'error messages in {0}:\n{1}'.format(caller, errors)
        return doc

    def _check_0(self, doc, xpath, msg):
        '''Check that there are no nodes of a particular type.'''
        nodes = doc.findall(xpath)
        assert len(nodes) == 0, (msg + ': got {0}'.format(len(nodes)))

    def _get_1(self, doc, xpath, msg):
        '''Get exactly one node from the document, checking that there _is_ exactly one.'''
        nodes = doc.findall(xpath)
        assert len(nodes) == 1, (msg + ': got {0}'.format(len(nodes)))
        return nodes[0]

    def _get_N(self, doc, xpath, msg, expected=None):
        '''Get all matching nodes from the document, checking the count if provided.'''
        nodes = doc.findall(xpath)
        if expected is not None:
            assert len(nodes) == expected, (msg + ': expected {0}, got {1}'.format(expected, len(nodes)))
        return nodes

    def _get_selected(self, node):
        '''Get value of currently selected element from 'select' node.'''
        selections = node.findall(".//option[@selected='selected']")
        if (len(selections) == 0):
            return ""
        if (len(selections) == 1):
            return selections[0].attrib['value']
        else:
            return ",".join([x.attrib['value'] for x in selections])

    def _get_initial_form_index(self, form_index, url, *args):
        '''Get a form to start testing with.

        If form_index is None, only 1 form is expected. Otherwise,
        forms[form_index] is returned from all matching forms.'''
        url = reverse(url, args=[str(a) for a in args])
        response = self.client.get(url)
        doc = self._check_status_code_and_parse(response, 200)
        self._save_html(response.content.decode("utf-8"))
        values = self._get_form_data(doc, form_index)
        return url, values

    def _get_initial_form(self, url, *args):
        '''Get first and only form on the page.'''
        return self._get_initial_form_index(None, url, *args)

    def _get_form_data(self, doc, which_form=None):
        '''Extract form data from page.'''
        # Now there's almost always an additional search form available on the
        # page, so we should fetch the one that does not have role="search".
        # We can't have such expression in ElementTree, though - 'cause it's
        # very limited.  Instead, I added a whole bunch of `role="form"` to
        # specific forms in create/update pages - we can match
        # `form[@role='form']` easily.
        if which_form is not None:
            # some pages have two forms that match this query, so we need to
            # specify which one do we use
            forms = self._get_N(doc, ".//form[@role='form']",
                                'expected multiple forms in page')
            form = forms[which_form]
        else:
            form = self._get_1(doc, ".//form[@role='form']",
                               'expected one form in page')

        inputs = dict([(i.attrib['name'], i.attrib.get('value', None))
                       for i in form.findall(".//input[@type='text']")])

        passwords = dict([(i.attrib['name'], i.attrib.get('value', None))
                          for i in form.findall(".//input[@type='password']")])

        hidden = dict([(i.attrib['name'], i.attrib.get('value', None))
                       for i in form.findall(".//input[@type='hidden']")])

        checkboxes = dict([(c.attrib['name'], c.attrib.get('checked', None)=='checked')
                           for c in form.findall(".//input[@type='checkbox']")])

        selects = dict([(s.attrib['name'], self._get_selected(s))
                        for s in form.findall('.//select')])

        textareas = dict([(t.attrib['name'], t.text)
                          for t in form.findall(".//textarea")])

        inputs.update(passwords)
        inputs.update(hidden)
        inputs.update(checkboxes)
        inputs.update(selects)
        inputs.update(textareas)
        return inputs

    def _save_html(self, content):
        caller = self._get_test_name_from_stack()
        if not os.path.isdir(self.ERR_DIR):
            os.mkdir(self.ERR_DIR)
        filename = os.path.join(self.ERR_DIR, '{0}.html'.format(caller))
        with open(filename, 'w') as writer:
            writer.write(content)

    def _collect_errors(self, doc):
        '''Check an HTML page to make sure there are no errors.'''
        errors = doc.findall(".//div[@class='form-group has-error']")
        if not errors:
            return

        error_msgs = []
        error_paths = ["./div/span[@class='help-block']/strong",
                       "./div/p[@class='help-block'/strong"]
        for path in error_paths:
            try:
                lines = [x.findall(path) for x in errors]
                lines = [x.text for x in list(itertools.chain(*lines))]
                error_msgs += lines

            # x.findall(path) raises SyntaxError if it's unable to find `path`
            except SyntaxError:
                pass

        return '\n'.join(error_msgs)

    def _get_test_name_from_stack(self):
        '''Walk up the stack to get the name of the calling test.'''
        stack = traceback.extract_stack()
        callers = [s[2] for s in stack] # get function/method names
        while callers and not callers[-1].startswith('test'):
            callers.pop()
        assert callers, 'Internal error: unable to find caller'
        caller = callers[-1]
        return caller
