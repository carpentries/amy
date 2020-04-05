from datetime import date, timedelta

from django.conf import settings
from django.urls import reverse

from autoemails.models import Trigger, EmailTemplate, RQJob
from autoemails.tests.base import FakeRedisTestCaseMixin
from extrequests.forms import WorkshopInquiryRequestBaseForm
from extrequests.models import WorkshopInquiryRequest, DataVariant
import extrequests.views
from workshops.forms import EventCreateForm
from workshops.models import (
    Tag,
    Task,
    Role,
    Event,
    Organization,
    Language,
    KnowledgeDomain,
    AcademicLevel,
    ComputingExperienceLevel,
    Curriculum,
    InfoSource,
)
from workshops.tests.base import TestBase, FormTestHelper


class TestWorkshopInquiryBaseForm(FormTestHelper, TestBase):
    """Test base form validation."""

    minimal_data = {
        'personal': 'Harry',
        'family': 'Potter',
        'email': 'hpotter@magic.gov',
        'institution_other_name': 'Ministry of Magic',
        'institution_other_URL': 'magic.gov.uk',
        'travel_expences_agreement': True,
        'location': 'London',
        'country': 'GB',
        'data_privacy_agreement': True,
        'code_of_conduct_agreement': True,
        'host_responsibilities': True,
    }

    def _test_dont_know_yet_option(self, Form, field, value_normal,
                                   value_dont_know_yet):
        data = self.minimal_data.copy()
        data[field] = [
            value_normal,
        ]
        form = Form(data)
        self.assertNotIn(field, form.errors)
        data[field] = [
            value_normal,
            value_dont_know_yet,
        ]
        form = Form(data)
        self.assertIn(field, form.errors)
        data[field] = [
            value_dont_know_yet,
        ]
        form = Form(data)
        self.assertNotIn(field, form.errors)

    def test_minimal_form(self):
        """Test if minimal form works."""
        data = self.minimal_data.copy()
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertTrue(form.is_valid(), dict(form.errors))

    def test_institution_validation(self):
        """Make sure institution data is present, and validation
        errors are triggered for various matrix of input data."""

        # 1: selected institution from the list
        data = {
            'institution': Organization.objects.first().pk,
            'institution_other_name': '',
            'institution_other_URL': '',
            'institution_department': 'School of Wizardry',
        }
        form = WorkshopInquiryRequestBaseForm(data)
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
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertNotIn('institution_other_name', form.errors)
        self.assertNotIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 3: no institution and no department
        #    contrary to WorkshopRequestBaseForm, this form doesn't require
        #    institution
        data = {
            'institution': '',
            'institution_other_name': '',
            'institution_other_URL': '',
            'institution_department': '',
        }
        form = WorkshopInquiryRequestBaseForm(data)
        # institution is NOT required
        self.assertNotIn('institution', form.errors)
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
        form = WorkshopInquiryRequestBaseForm(data)
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
        form = WorkshopInquiryRequestBaseForm(data)
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
        form = WorkshopInquiryRequestBaseForm(data)
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
        form = WorkshopInquiryRequestBaseForm(data)
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
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertIn('institution_other_name', form.errors)
        self.assertIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

    def test_dont_know_yet(self):
        """Make sure selecting 'Don't know yet' + other option in various
        fields yields errors."""
        # 1: routine data, domains, academic levels, computing levels and
        #    requested workshop types are not required
        data = self.minimal_data.copy()
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertNotIn('routine_data', form.errors)
        self.assertNotIn('domains', form.errors)
        self.assertNotIn('academic_levels', form.errors)
        self.assertNotIn('computing_levels', form.errors)
        self.assertNotIn('requested_workshop_types', form.errors)

        # 2: routine data
        self._test_dont_know_yet_option(
            Form=WorkshopInquiryRequestBaseForm,
            field='routine_data',
            value_normal=DataVariant.objects.filter(unknown=False).first().pk,
            value_dont_know_yet=DataVariant.objects.filter(unknown=True)
                                                   .first().pk,
        )
        # additionally test against `routine_data_other`
        data = self.minimal_data.copy()
        data['routine_data'] = [DataVariant.objects.filter(unknown=True)
                                                   .first().pk]
        data['routine_data_other'] = 'Other routine data'
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertIn('routine_data', form.errors)

        # 3: domains
        self._test_dont_know_yet_option(
            Form=WorkshopInquiryRequestBaseForm,
            field='domains',
            value_normal=KnowledgeDomain.objects.exclude(name="Don't know yet")
                                                .first().pk,
            value_dont_know_yet=KnowledgeDomain.objects
                                               .filter(name="Don't know yet")
                                               .first().pk,
        )
        # additionally test against `domains_other`
        data = self.minimal_data.copy()
        data['domains'] = [KnowledgeDomain.objects
                                               .filter(name="Don't know yet")
                                               .first().pk]
        data['domains_other'] = 'Other domains'
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertIn('domains', form.errors)

        # 4: academic levels
        self._test_dont_know_yet_option(
            Form=WorkshopInquiryRequestBaseForm,
            field='academic_levels',
            value_normal=AcademicLevel.objects.exclude(name="Don't know yet")
                                              .first().pk,
            value_dont_know_yet=AcademicLevel.objects
                                             .filter(name="Don't know yet")
                                             .first().pk,
        )

        # 5: computing levels
        self._test_dont_know_yet_option(
            Form=WorkshopInquiryRequestBaseForm,
            field='computing_levels',
            value_normal=ComputingExperienceLevel.objects
                                                .exclude(name="Don't know yet")
                                                .first().pk,
            value_dont_know_yet=ComputingExperienceLevel.objects
                                                .filter(name="Don't know yet")
                                                .first().pk,
        )

        # 6: requested workshop types
        base_curriculum = Curriculum.objects.default_order(allow_other=True,
                                                           allow_unknown=True)\
                                            .filter(active=True)
        self._test_dont_know_yet_option(
            Form=WorkshopInquiryRequestBaseForm,
            field='requested_workshop_types',
            value_normal=base_curriculum.filter(unknown=False).first().pk,
            value_dont_know_yet=base_curriculum.filter(unknown=True).first().pk,
        )

    def test_dates_validation(self):
        """Ensure preferred dates validation."""
        # 1: both empty won't trigger error - the field is not required
        data = {
            'preferred_dates': '',
            'other_preferred_dates': '',
        }
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertNotIn('preferred_dates', form.errors)
        self.assertNotIn('other_preferred_dates', form.errors)

        # 2: either one present will work
        data = {
            'preferred_dates': '{:%Y-%m-%d}'.format(date.today()),
            'other_preferred_dates': '',
        }
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertNotIn('preferred_dates', form.errors)
        self.assertNotIn('other_preferred_dates', form.errors)

        data = {
            'preferred_dates': '',
            'other_preferred_dates': 'Next weekend',
        }
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertNotIn('preferred_dates', form.errors)
        self.assertNotIn('other_preferred_dates', form.errors)

        # 3: preferred date from the past
        data = {
            'preferred_dates': '2000-01-01',
            'other_preferred_dates': '',
        }
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertIn('preferred_dates', form.errors)
        self.assertNotIn('other_preferred_dates', form.errors)

        # 4: preferred date wrong format
        data = {
            'preferred_dates': '{:%d-%m-%Y}'.format(date.today()),
            'other_preferred_dates': '',
        }
        form = WorkshopInquiryRequestBaseForm(data)
        self.assertIn('preferred_dates', form.errors)
        self.assertNotIn('other_preferred_dates', form.errors)

    def test_travel_expences_management(self):
        """Test validation of travel expences management."""
        self._test_field_other(
            Form=WorkshopInquiryRequestBaseForm,
            first_name='travel_expences_management',
            other_name='travel_expences_management_other',
            valid_first='reimbursed',
            valid_other="Local instructors don't need reimbursement",
            first_when_other="other",
            blank=True,
        )

    def test_institution_restrictions(self):
        """Test validation of institution restrictions."""
        self._test_field_other(
            Form=WorkshopInquiryRequestBaseForm,
            first_name='institution_restrictions',
            other_name='institution_restrictions_other',
            valid_first='no_restrictions',
            valid_other='Visa required',
            first_when_other="other",
            blank=True,
        )

    def test_public_event(self):
        """Test validation of event's openness to public."""
        self._test_field_other(
            Form=WorkshopInquiryRequestBaseForm,
            first_name='public_event',
            other_name='public_event_other',
            valid_first='public',
            valid_other='Open to conference attendees',
            first_when_other="other",
            blank=True,
        )


class TestWorkshopInquiryViews(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()

        self.wi1 = WorkshopInquiryRequest.objects.create(
            state="p", personal="Harry", family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            institution_other_URL='hogwarts.uk',
            location="Scotland", country="GB",
            routine_data_other="",
            domains_other="",
            audience_description="Students of Hogwarts",
            preferred_dates=None, other_preferred_dates="soon",
            language=Language.objects.get(name='English'),
            number_attendees='10-40',
            administrative_fee='nonprofit',
            travel_expences_management='booked',
            travel_expences_management_other='',
            travel_expences_agreement=True,
            institution_restrictions='no_restrictions',
            institution_restrictions_other='',
            public_event='invite',
            carpentries_info_source_other='',
            user_notes='n/c',
        )
        self.wi2 = WorkshopInquiryRequest.objects.create(
            state="d", personal="Harry", family="Potter",
            email="harry@potter.com",
            institution_other_name="Hogwarts",
            institution_other_URL='hogwarts.uk',
            location="Scotland", country="GB",
            routine_data_other="",
            domains_other="",
            audience_description="Students of Hogwarts",
            preferred_dates=None, other_preferred_dates="soon",
            language=Language.objects.get(name='English'),
            number_attendees='40-80',
            administrative_fee='forprofit',
            travel_expences_management='reimbursed',
            travel_expences_management_other='',
            travel_expences_agreement=True,
            institution_restrictions='other',
            institution_restrictions_other='Visa required',
            public_event='public',
            carpentries_info_source_other='',
            user_notes='n/c',
        )

    def test_pending_requests_list(self):
        rv = self.client.get(reverse('all_workshopinquiries'))
        self.assertIn(self.wi1, rv.context['inquiries'])
        self.assertNotIn(self.wi2, rv.context['inquiries'])

    def test_discarded_requests_list(self):
        rv = self.client.get(reverse('all_workshopinquiries') + '?state=d')
        self.assertNotIn(self.wi1, rv.context['inquiries'])
        self.assertIn(self.wi2, rv.context['inquiries'])

    def test_set_state_pending_request_view(self):
        rv = self.client.get(reverse('workshopinquiry_set_state',
                                     args=[self.wi1.pk, 'discarded']))
        self.assertEqual(rv.status_code, 302)
        self.wi1.refresh_from_db()
        self.assertEqual(self.wi1.state, "d")

    def test_set_state_discarded_request_view(self):
        rv = self.client.get(reverse('workshopinquiry_set_state',
                                     args=[self.wi2.pk, 'discarded']))
        self.assertEqual(rv.status_code, 302)
        self.wi2.refresh_from_db()
        self.assertEqual(self.wi2.state, "d")

    def test_pending_request_accept(self):
        rv = self.client.get(reverse('workshopinquiry_set_state',
                                     args=[self.wi1.pk, 'accepted']))
        self.assertEqual(rv.status_code, 302)

    def test_pending_request_accepted_with_event(self):
        """Ensure a backlink from Event to WorkshopInquiryRequest that created the
        event exists after ER is accepted."""
        data = {
            'slug': '2018-10-28-test-event',
            'host': Organization.objects.first().pk,
            'tags': [1],
            'invoice_status': 'unknown',
        }
        rv = self.client.post(
            reverse('workshopinquiry_accept_event', args=[self.wi1.pk]),
            data)
        self.assertEqual(rv.status_code, 302)
        request = Event.objects.get(slug='2018-10-28-test-event') \
                               .workshopinquiryrequest
        self.assertEqual(request, self.wi1)

    def test_discarded_request_not_accepted_with_event(self):
        rv = self.client.get(reverse('workshopinquiry_accept_event',
                                     args=[self.wi2.pk]))
        self.assertEqual(rv.status_code, 404)

    def test_pending_request_discard(self):
        rv = self.client.get(reverse('workshopinquiry_set_state',
                                     args=[self.wi1.pk, 'discarded']),
                             follow=True)
        self.assertEqual(rv.status_code, 200)

    def test_discarded_request_discard(self):
        rv = self.client.get(reverse('workshopinquiry_set_state',
                                     args=[self.wi2.pk, 'discarded']),
                             follow=True)
        self.assertEqual(rv.status_code, 200)

    def test_discarded_request_reopened(self):
        self.wi1.state = "a"
        self.wi1.save()
        self.client.get(
            reverse('workshopinquiry_set_state',
                    args=[self.wi1.pk, 'pending']),
            follow=True)
        self.wi1.refresh_from_db()
        self.assertEqual(self.wi1.state, "p")

    def test_accepted_request_reopened(self):
        self.assertEqual(self.wi2.state, "d")
        self.client.get(
            reverse('workshopinquiry_set_state',
                    args=[self.wi2.pk, 'pending']),
            follow=True)
        self.wi2.refresh_from_db()
        self.assertEqual(self.wi2.state, "p")

    def test_list_no_comments(self):
        """Regression for #1435: missing "comment" field displayed on "all
        workshops" page.

        https://github.com/swcarpentry/amy/issues/1435

        This test was backported from WorkshopRequest tests.
        """

        # make sure the `string_if_invalid` is not empty
        self.assertTrue(settings.TEMPLATES[0]['OPTIONS']['string_if_invalid'])

        rv = self.client.get(reverse('all_workshopinquiries'))

        # some objects available in the page
        self.assertNotEqual(len(rv.context['inquiries']), 0)

        # no string_if_invalid found in the page
        invalid = settings.TEMPLATES[0]['OPTIONS']['string_if_invalid']
        self.assertNotIn(invalid, rv.content.decode('utf-8'))


class TestAcceptingWorkshopInquiry(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()

        self.wi1 = WorkshopInquiryRequest.objects.create(
            state="p", personal="Harry", family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            institution_other_URL='hogwarts.uk',
            location="Scotland", country="GB",
            routine_data_other="",
            domains_other="",
            audience_description="Students of Hogwarts",
            preferred_dates=None, other_preferred_dates="soon",
            language=Language.objects.get(name='English'),
            number_attendees='10-40',
            administrative_fee='nonprofit',
            travel_expences_management='booked',
            travel_expences_management_other='',
            travel_expences_agreement=True,
            institution_restrictions='no_restrictions',
            institution_restrictions_other='',
            public_event='invite',
            carpentries_info_source_other='',
            user_notes='n/c',
        )

        self.url = reverse('workshopinquiry_accept_event',
                           args=[self.wi1.pk])

    def test_page_context(self):
        """Ensure proper objects render in the page."""
        rv = self.client.get(self.url)
        self.assertIn('form', rv.context)
        self.assertIn('object', rv.context)  # this is our request
        form = rv.context['form']
        wi = rv.context['object']
        self.assertEqual(wi, self.wi1)
        self.assertTrue(isinstance(form, EventCreateForm))

    def test_state_changed(self):
        """Ensure request's state is changed after accepting."""
        self.assertTrue(self.wi1.state == 'p')
        data = {
            'slug': '2018-10-28-test-event',
            'host': Organization.objects.first().pk,
            'tags': [1],
        }
        rv = self.client.post(self.url, data)
        self.assertEqual(rv.status_code, 302)
        self.wi1.refresh_from_db()
        self.assertTrue(self.wi1.state == 'a')

    def test_host_task_created(self):
        """Ensure a host task is created when a person submitting the inquiry
        already is in our database."""

        # Harry matched as a submitted for self.wi1, and he has no tasks so far
        self.assertEqual(self.wi1.host(), self.harry)
        self.assertFalse(self.harry.task_set.all())

        # create event from that workshop inquiry
        data = {
            'slug': '2019-08-18-test-event',
            'host': Organization.objects.first().pk,
            'tags': [1],
        }
        rv = self.client.post(self.url, data)
        self.assertEqual(rv.status_code, 302)
        event = Event.objects.get(slug='2019-08-18-test-event')

        # check if Harry gained a task
        Task.objects.get(person=self.harry, event=event,
                         role=Role.objects.get(name="host"))


class TestAcceptWorkshopInquiryAddsEmailAction(FakeRedisTestCaseMixin,
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

        self.wi1 = WorkshopInquiryRequest.objects.create(
            state="p", personal="Harry", family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            institution_other_URL='hogwarts.uk',
            location="Scotland", country="GB",
            routine_data_other="",
            domains_other="",
            audience_description="Students of Hogwarts",
            preferred_dates=None, other_preferred_dates="soon",
            language=Language.objects.get(name='English'),
            number_attendees='10-40',
            administrative_fee='nonprofit',
            travel_expences_management='booked',
            travel_expences_management_other='',
            travel_expences_agreement=True,
            institution_restrictions='no_restrictions',
            institution_restrictions_other='',
            public_event='invite',
            carpentries_info_source_other='',
            user_notes='n/c',
        )

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
        self.trigger1 = Trigger.objects.create(
            action='week-after-workshop-completion',
            template=template1,
        )

        self.url = reverse('workshopinquiry_accept_event',
                           args=[self.wi1.pk])

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
        request = event.workshopinquiryrequest
        self.assertEqual(request, self.wi1)

        # 1 job created
        rqjobs_post = RQJob.objects.all()
        self.assertEqual(len(rqjobs_post), 1)

        # ensure the job ids are mentioned in the page output
        content = rv.content.decode('utf-8')
        for job in rqjobs_post:
            self.assertIn(job.job_id, content)

        # ensure the job is for PostWorkshopAction
        rqjobs_post[0].trigger = self.trigger1
