from datetime import date, timedelta

from django.conf import settings
from django.urls import reverse
from requests_mock import Mocker

from autoemails.models import Trigger, EmailTemplate, RQJob
from autoemails.tests.base import FakeRedisTestCaseMixin
from extrequests.forms import SelfOrganisedSubmissionBaseForm
from extrequests.models import SelfOrganisedSubmission
import extrequests.views
from workshops.forms import EventCreateForm
from workshops.models import (
    Task,
    Role,
    Event,
    Organization,
    Language,
    Curriculum,
    Tag,
)
from workshops.tests.base import TestBase, FormTestHelper


class TestSelfOrganisedSubmissionBaseForm(FormTestHelper, TestBase):
    """Test base form validation."""

    def setUp(self):
        super().setUp()
        self.minimal_data = {
            'personal': 'Harry',
            'family': 'Potter',
            'email': 'hpotter@magic.gov',
            'institution_other_name': 'Ministry of Magic',
            'institution_other_URL': 'magic.gov.uk',
            'workshop_format': 'periodic',
            'workshop_format_other': '',
            'workshop_url': '',
            'workshop_types': [
                Curriculum.objects.filter(active=True)
                                  .exclude(mix_match=True)
                                  .first().pk,
            ],
            'workshop_types_other_explain': '',
            'country': 'GB',
            'language':  Language.objects.get(name='English').pk,
            'public_event': 'closed',
            'public_event_other': '',
            'additional_contact': '',
            'data_privacy_agreement': True,
            'code_of_conduct_agreement': True,
            'host_responsibilities': True,
            "online_inperson": "inperson",
        }

    def test_minimal_form(self):
        """Test if minimal form works."""
        data = self.minimal_data.copy()
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertTrue(form.is_valid(), dict(form.errors))

    def test_institution_validation(self):
        """Make sure institution data is present, and validation
        errors are triggered for various matrix of input data."""

        # 1: selected institution from the list
        data = {
            'institution': Organization.objects
                                       .exclude(fullname='self-organised')
                                       .first().pk,
            'institution_other_name': '',
            'institution_other_URL': '',
            'institution_department': 'School of Wizardry',
        }
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertNotIn('institution_other_name', form.errors)
        self.assertNotIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 2: institution name manually entered
        data = {
            'institution': '',
            'institution_other_name': 'Hogwarts',
            'institution_other_URL': 'hogwarts.uk',
            'institution_department': 'School of Wizardry',
        }
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertNotIn('institution_other_name', form.errors)
        self.assertNotIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 3: no institution and no department
        data = {
            'institution': '',
            'institution_other_name': '',
            'institution_other_URL': '',
            'institution_department': '',
        }
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertIn('institution', form.errors)  # institution is required
        self.assertNotIn('institution_other_name', form.errors)
        self.assertNotIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 4: other name, but no other URL (+ no institution)
        data = {
            'institution': '',
            'institution_other_name': 'Hogwarts',
            'institution_other_URL': '',
            'institution_department': '',
        }
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertIn('institution_other_name', form.errors)
        self.assertNotIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 5: other URL, but no other name (+ no institution)
        data = {
            'institution': '',
            'institution_other_name': '',
            'institution_other_URL': 'hogwarts.uk',
            'institution_department': '',
        }
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertIn('institution_other_name', form.errors)
        self.assertNotIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 6: institution, other name, no other URL
        data = {
            'institution': Organization.objects.first().pk,
            'institution_other_name': 'Hogwarts',
            'institution_other_URL': '',
            'institution_department': '',
        }
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertIn('institution_other_name', form.errors)
        self.assertNotIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 7: institution, other URL, no other name
        data = {
            'institution': Organization.objects.first().pk,
            'institution_other_name': '',
            'institution_other_URL': 'hogwarts.uk',
            'institution_department': '',
        }
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertNotIn('institution_other_name', form.errors)
        self.assertIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 8: wrong URL format
        data = {
            'institution': '',
            'institution_other_name': 'Hogwarts',
            'institution_other_URL': 'wrong_url',
            'institution_department': '',
        }
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertIn('institution_other_name', form.errors)
        self.assertIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

    def test_workshop_URL(self):
        """Test validation of workshop URL."""
        # 1: required only when workshop format is "standard" 2-day workshop
        data = self.minimal_data.copy()
        data['workshop_format'] = 'short'
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('workshop_format', form.errors)
        self.assertNotIn('workshop_url', form.errors)

        data['workshop_format'] = 'standard'
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('workshop_format', form.errors)
        self.assertIn('workshop_url', form.errors)

        data['workshop_url'] = 'https://github.com/'
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('workshop_format', form.errors)
        self.assertNotIn('workshop_url', form.errors)

        # 2: wrong URL
        data = self.minimal_data.copy()
        data['workshop_url'] = 'not_an_URL'
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertIn('workshop_url', form.errors)

    def test_workshop_format(self):
        """Test validation of workshop format."""
        self._test_field_other(
            Form=SelfOrganisedSubmissionBaseForm,
            first_name='workshop_format',
            other_name='workshop_format_other',
            valid_first='short',
            valid_other='Other workshop format',
            first_when_other='other',
        )

    def test_workshop_types(self):
        """Test validation of workshop types explanation."""
        curricula = Curriculum.objects.default_order(allow_other=False,
                                                     allow_unknown=False,
                                                     allow_mix_match=True) \
                                      .filter(active=True)

        # 1: required only when workshop types is "mix & match"
        data = self.minimal_data.copy()
        data['workshop_types'] = [curricula.exclude(mix_match=True).first().pk]
        data['workshop_types_other_explain'] = ("It doesn't matter when "
                                                "mix&match is not selected.")
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('workshop_types', form.errors)
        self.assertNotIn('workshop_types_other_explain', form.errors)

        # 2: error when mix&match but no explanation
        data = self.minimal_data.copy()
        data['workshop_types'] = [curricula.filter(mix_match=True).first().pk]
        data['workshop_types_other_explain'] = ""
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('workshop_types', form.errors)
        self.assertIn('workshop_types_other_explain', form.errors)

        # 3: error fixed
        data = self.minimal_data.copy()
        data['workshop_types'] = [curricula.filter(mix_match=True).first().pk]
        data['workshop_types_other_explain'] = ("It does matter when "
                                                "mix&match is selected.")
        form = SelfOrganisedSubmissionBaseForm(data)
        self.assertNotIn('workshop_types', form.errors)
        self.assertNotIn('workshop_types_other_explain', form.errors)

    def test_public_event(self):
        """Test validation of event's openness to public."""
        self._test_field_other(
            Form=SelfOrganisedSubmissionBaseForm,
            first_name='public_event',
            other_name='public_event_other',
            valid_first='public',
            valid_other='Open to conference attendees',
            first_when_other="other",
        )


class TestSelfOrganisedSubmissionViews(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()

        self.sos1 = SelfOrganisedSubmission.objects.create(
            state="p", personal="Harry", family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url='',
            workshop_format='',
            workshop_format_other='',
            workshop_types_other_explain='',
            language=Language.objects.get(name='English'),
        )
        self.sos1.workshop_types.set(Curriculum.objects.filter(mix_match=True))

        self.sos2 = SelfOrganisedSubmission.objects.create(
            state="d", personal="Harry", family="Potter",
            email="harry@potter.com",
            institution_other_name="Hogwarts",
            workshop_url='',
            workshop_format='',
            workshop_format_other='',
            workshop_types_other_explain='',
            language=Language.objects.get(name='English'),
        )
        self.sos2.workshop_types.set(
            Curriculum.objects.filter(mix_match=False, unknown=False,
                                      other=False)[:1]
        )

    def test_pending_requests_list(self):
        rv = self.client.get(reverse('all_selforganisedsubmissions'))
        self.assertIn(self.sos1, rv.context['submissions'])
        self.assertNotIn(self.sos2, rv.context['submissions'])

    def test_discarded_requests_list(self):
        rv = self.client.get(reverse('all_selforganisedsubmissions') + '?state=d')
        self.assertNotIn(self.sos1, rv.context['submissions'])
        self.assertIn(self.sos2, rv.context['submissions'])

    def test_set_state_pending_request_view(self):
        rv = self.client.get(reverse('selforganisedsubmission_set_state',
                                     args=[self.sos1.pk, 'discarded']))
        self.assertEqual(rv.status_code, 302)
        self.sos1.refresh_from_db()
        self.assertEqual(self.sos1.state, "d")

    def test_set_state_discarded_request_view(self):
        rv = self.client.get(reverse('selforganisedsubmission_set_state',
                                     args=[self.sos2.pk, 'discarded']))
        self.assertEqual(rv.status_code, 302)
        self.sos2.refresh_from_db()
        self.assertEqual(self.sos2.state, "d")

    def test_pending_request_accept(self):
        rv = self.client.get(reverse('selforganisedsubmission_set_state',
                                     args=[self.sos1.pk, 'accepted']))
        self.assertEqual(rv.status_code, 302)

    def test_pending_request_accepted_with_event(self):
        """Ensure a backlink from Event to SelfOrganisedSubmission that created
        the event exists after ER is accepted."""
        data = {
            'slug': '2018-10-28-test-event',
            'host': Organization.objects.first().pk,
            'administrator': Organization.objects.administrators().first().id,
            'tags': [1],
        }
        rv = self.client.post(
            reverse('selforganisedsubmission_accept_event',
                    args=[self.sos1.pk]),
            data)
        self.assertEqual(rv.status_code, 302)
        request = Event.objects.get(slug='2018-10-28-test-event') \
                               .selforganisedsubmission
        self.assertEqual(request, self.sos1)

    def test_discarded_request_not_accepted_with_event(self):
        rv = self.client.get(reverse('selforganisedsubmission_accept_event',
                                     args=[self.sos2.pk]))
        self.assertEqual(rv.status_code, 404)

    def test_pending_request_discard(self):
        rv = self.client.get(reverse('selforganisedsubmission_set_state',
                                     args=[self.sos1.pk, 'discarded']),
                             follow=True)
        self.assertEqual(rv.status_code, 200)

    def test_discarded_request_discard(self):
        rv = self.client.get(reverse('selforganisedsubmission_set_state',
                                     args=[self.sos2.pk, 'discarded']),
                             follow=True)
        self.assertEqual(rv.status_code, 200)

    def test_discarded_request_reopened(self):
        self.sos1.state = "a"
        self.sos1.save()
        self.client.get(
            reverse('selforganisedsubmission_set_state',
                    args=[self.sos1.pk, 'pending']),
            follow=True)
        self.sos1.refresh_from_db()
        self.assertEqual(self.sos1.state, "p")

    def test_accepted_request_reopened(self):
        self.assertEqual(self.sos2.state, "d")
        self.client.get(
            reverse('selforganisedsubmission_set_state',
                    args=[self.sos2.pk, 'pending']),
            follow=True)
        self.sos2.refresh_from_db()
        self.assertEqual(self.sos2.state, "p")

    def test_list_no_comments(self):
        """Regression for #1435: missing "comment" field displayed on "all
        workshops" page.

        https://github.com/swcarpentry/amy/issues/1435

        This test was backported from WorkshopRequest tests.
        """

        # make sure the `string_if_invalid` is not empty
        self.assertTrue(settings.TEMPLATES[0]['OPTIONS']['string_if_invalid'])

        rv = self.client.get(reverse('all_selforganisedsubmissions'))

        # some objects available in the page
        self.assertNotEqual(len(rv.context['submissions']), 0)

        # no string_if_invalid found in the page
        invalid = settings.TEMPLATES[0]['OPTIONS']['string_if_invalid']
        self.assertNotIn(invalid, rv.content.decode('utf-8'))


class TestAcceptingSelfOrgSubmission(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()

        self.sos1 = SelfOrganisedSubmission.objects.create(
            state="p", personal="Harry", family="Potter",
            email="harry@hogwarts.edu",
            institution=self.org_alpha,
            institution_other_name="Hogwarts",
            workshop_url='http://nonexistent-url/',
            workshop_format='',
            workshop_format_other='',
            workshop_types_other_explain='',
            language=Language.objects.get(name='English'),
        )
        self.sos1.workshop_types.set(Curriculum.objects.filter(mix_match=True))

        self.url = reverse('selforganisedsubmission_accept_event',
                           args=[self.sos1.pk])

        self.sos2 = SelfOrganisedSubmission.objects.create(
            state="d", personal="Harry", family="Potter",
            email="harry@potter.com",
            institution_other_name="Hogwarts",
            workshop_url='',
            workshop_format='',
            workshop_format_other='',
            workshop_types_other_explain='',
            language=Language.objects.get(name='English'),
        )
        self.sos2.workshop_types.set(
            Curriculum.objects.filter(mix_match=False, unknown=False,
                                      other=False)[:1]
        )
        self.url2 = reverse('selforganisedsubmission_accept_event',
                            args=[self.sos2.pk])

    def test_page_context(self):
        """Ensure proper objects render in the page."""
        rv = self.client.get(self.url)
        self.assertIn('form', rv.context)
        self.assertIn('object', rv.context)  # this is our request
        form = rv.context['form']
        sos = rv.context['object']
        self.assertEqual(sos, self.sos1)
        self.assertTrue(isinstance(form, EventCreateForm))

    def test_state_changed(self):
        """Ensure request's state is changed after accepting."""
        self.assertTrue(self.sos1.state == 'p')
        data = {
            'slug': '2018-10-28-test-event',
            'host': Organization.objects.first().pk,
            'administrator': Organization.objects.administrators().first().id,
            'tags': [1],
        }
        rv = self.client.post(self.url, data)
        self.assertEqual(rv.status_code, 302)
        self.sos1.refresh_from_db()
        self.assertTrue(self.sos1.state == 'a')

    def test_host_task_created(self):
        """Ensure a host task is created when a person submitting already is in
        our database."""

        # Harry matched as a submitted for self.sos1, and he has no tasks
        # so far
        self.assertEqual(self.sos1.host(), self.harry)
        self.assertFalse(self.harry.task_set.all())

        # create event from that workshop inquiry
        data = {
            'slug': '2019-08-18-test-event',
            'host': Organization.objects.first().pk,
            'administrator': Organization.objects.administrators().first().id,
            'tags': [1],
        }
        rv = self.client.post(self.url, data)
        self.assertEqual(rv.status_code, 302)
        event = Event.objects.get(slug='2019-08-18-test-event')

        # check if Harry gained a task
        Task.objects.get(person=self.harry, event=event,
                         role=Role.objects.get(name="host"))

    def test_lessons_hidden_in_event_create_form(self):
        """Ensure Mix&Match doesn't trigger "lessons" field on EventCreateForm."""
        # self.sos1 has Mix&Match workshop type, so it should hide "lessons"
        # field in Event form
        rv = self.client.get(self.url)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(Curriculum.objects.get(mix_match=True),
                      self.sos1.workshop_types.all())
        self.assertNotIn("lessons", rv.context["form"].fields.keys())

        # self.sos2 doesn't have Mix&Match workshop type, and the "lessons" field
        # should remain hidden in Event form
        self.sos2.state = "p"
        self.sos2.save()
        rv = self.client.get(self.url2)
        self.assertEqual(rv.status_code, 200)
        self.assertNotIn(Curriculum.objects.get(mix_match=True),
                         self.sos2.workshop_types.all())
        self.assertNotIn("lessons", rv.context["form"].fields.keys())


class TestAcceptingSelfOrgSubmPrefilledform(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()

        self.sos1 = SelfOrganisedSubmission.objects.create(
            state="p", personal="Harry", family="Potter",
            email="harry@hogwarts.edu",
            institution=self.org_alpha,
            institution_other_name="Hogwarts",
            workshop_url='http://nonexistent-url/',
            workshop_format='',
            workshop_format_other='',
            workshop_types_other_explain='',
            language=Language.objects.get(name='English'),
        )
        self.sos1.workshop_types.set(Curriculum.objects.filter(mix_match=True))

    def test_form_prefilled_not_from_URL(self):
        """Ensure even though URL isn't working, the form gets some fields
        with initial values."""
        view_url = reverse('selforganisedsubmission_accept_event',
                           args=[self.sos1.pk])
        page = self.client.get(view_url)
        form = page.context['form']

        # assert we see the warning
        self.assertIn("Cannot automatically fill the form",
                      page.content.decode('utf-8'))

        expected = {
            # fields below are pre-filled without accessing the website
            'url': "http://nonexistent-url/",
            'curricula': [Curriculum.objects.get(mix_match=True)],
            'host': self.org_alpha,
            'administrator': Organization.objects.get(domain="self-organized"),
            'tags': [Tag.objects.get(name="Circuits")],

            # fields below can't get populated because the website doesn't
            # work
            'slug': None,
            'language': None,
            'start': None,
            'end': None,
            'country': None,
            'venue': '',
            'address': '',
            'latitude': None,
            'longitude': None,
            'reg_key': None,
            'contact': '',
            'comment': None,
        }
        for key, value in expected.items():
            init = form[key].initial
            self.assertEqual(init, value, f"Issue with {key}")

    @Mocker()
    def test_form_prefilled_from_URL(self, mock):
        """Ensure the form gets fields populated both from Self-Organised Subm.
        and from the workshop page."""
        html = """
            <html><head>
            <meta name="slug" content="2020-04-04-test" />
            <meta name="startdate" content="2020-04-04" />
            <meta name="enddate" content="2020-04-05" />
            <meta name="country" content="us" />
            <meta name="venue" content="Euphoric State University" />
            <meta name="address" content="Highway to Heaven 42, Academipolis" />
            <meta name="latlng" content="36.998977, -109.045173" />
            <meta name="language" content="en" />
            <meta name="invalid" content="invalid" />
            <meta name="instructor" content="Hermione Granger|Ron Weasley" />
            <meta name="helper" content="Peter Parker|Tony Stark|Natasha Romanova" />
            <meta name="contact" content="hermione@granger.co.uk|rweasley@ministry.gov" />
            <meta name="eventbrite" content="10000000" />
            <meta name="charset" content="utf-8" />
            </head>
            <body>
            <h1>test</h1>
            </body></html>
        """
        # setup mock to "fake" the response from non-existing URL
        mock.get(
            self.sos1.workshop_url,
            text=html,
            status_code=200,
        )

        view_url = reverse('selforganisedsubmission_accept_event',
                           args=[self.sos1.pk])
        page = self.client.get(view_url)
        form = page.context['form']

        # assert we see the warning
        self.assertNotIn("Cannot automatically fill the form",
                         page.content.decode('utf-8'))
        self.assertNotIn("Cannot automatically fill language",
                         page.content.decode('utf-8'))

        expected = {
            # fields below are pre-filled without accessing the website
            'url': "http://nonexistent-url/",
            'curricula': [Curriculum.objects.get(mix_match=True)],
            'host': self.org_alpha,
            'administrator': Organization.objects.get(domain="self-organized"),
            'tags': [Tag.objects.get(name="Circuits")],

            # fields below are pre-filled from the website meta tags
            'slug': "2020-04-04-test",
            'language': Language.objects.get(subtag="en"),
            'start': date(2020, 4, 4),
            'end': date(2020, 4, 5),
            'country': "US",
            'venue': "Euphoric State University",
            'address': "Highway to Heaven 42, Academipolis",
            'latitude': 36.998977,
            'longitude': -109.045173,
            'reg_key': 10000000,
            'contact': ["hermione@granger.co.uk", "rweasley@ministry.gov"],
            'comment': "Instructors: Hermione Granger,Ron Weasley\n\n"
                       "Helpers: Peter Parker,Tony Stark,Natasha Romanova",
        }
        for key, value in expected.items():
            init = form[key].initial
            self.assertEqual(init, value, f"Issue with {key}")


class TestAcceptSelfOrganisedSubmissionAddsEmailActions(FakeRedisTestCaseMixin,
                                                        TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()
        # we're missing some tags
        Tag.objects.bulk_create([
            Tag(name='SWC'),
            Tag(name='DC'),
            Tag(name='LC'),
            Tag(name='TTT'),
            Tag(name='automated-email'),
        ])

        self.sos = SelfOrganisedSubmission.objects.create(
            state="p", personal="Harry", family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            workshop_url='',
            workshop_format='',
            workshop_format_other='',
            workshop_types_other_explain='',
            language=Language.objects.get(name='English'),
            additional_contact='hg@magic.uk',
        )
        self.sos.workshop_types.set(Curriculum.objects.filter(carpentry="LC"))

        template1 = EmailTemplate.objects.create(
            slug='sample-template1',
            subject='Welcome to {{ site.name }}',
            to_header='recipient@address.com',
            from_header='test@address.com',
            cc_header='copy@example.org',
            bcc_header='bcc@example.org',
            reply_to_header='{{ reply_to }}',
            body_template="Sample text.",
        )
        template2 = EmailTemplate.objects.create(
            slug='sample-template2',
            subject='Welcome to {{ site.name }}',
            to_header='recipient@address.com',
            from_header='test@address.com',
            cc_header='copy@example.org',
            bcc_header='bcc@example.org',
            reply_to_header='{{ reply_to }}',
            body_template="Sample text.",
        )
        self.trigger1 = Trigger.objects.create(
            action='self-organised-request-form',
            template=template1,
        )
        self.trigger2 = Trigger.objects.create(
            action='week-after-workshop-completion',
            template=template2,
        )

        self.url = reverse('selforganisedsubmission_accept_event',
                           args=[self.sos.pk])

        # save scheduler and connection data
        self._saved_scheduler = extrequests.views.scheduler
        self._saved_redis_connection = extrequests.views.redis_connection
        # overwrite them
        extrequests.views.scheduler = self.scheduler
        extrequests.views.redis_connection = self.connection

    def tearDown(self):
        super().tearDown()
        extrequests.views.scheduler = self._saved_scheduler
        extrequests.views.redis_connection = self._saved_redis_connection

    def test_jobs_created(self):
        data = {
            'slug': 'xxxx-xx-xx-test-event',
            'host': Organization.objects.first().pk,
            'administrator': Organization.objects
                                         .get(domain='self-organized').pk,
            'start': date.today() + timedelta(days=7),
            'end': date.today() + timedelta(days=8),
            'tags': Tag.objects.filter(name__in=['automated-email', 'LC'])
                       .values_list('pk', flat=True),
        }

        # no jobs scheduled
        rqjobs_pre = RQJob.objects.all()
        self.assertQuerysetEqual(rqjobs_pre, [])

        # send data in
        rv = self.client.post(self.url, data, follow=True)
        self.assertEqual(rv.status_code, 200)
        event = Event.objects.get(slug='xxxx-xx-xx-test-event')
        request = event.selforganisedsubmission
        self.assertEqual(request, self.sos)

        # 2 jobs created
        rqjobs_post = RQJob.objects.all()
        self.assertEqual(len(rqjobs_post), 2)

        # ensure the job ids are mentioned in the page output
        content = rv.content.decode('utf-8')
        for job in rqjobs_post:
            self.assertIn(job.job_id, content)

        # ensure 1 job is for SelfOrganisedRequestAction,
        # and 1 for PostWorkshopAction
        rqjobs_post[0].trigger = self.trigger1
        rqjobs_post[1].trigger = self.trigger2
