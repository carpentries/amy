import datetime

from django.conf import settings
from django.urls import reverse

from extrequests.forms import SelfOrganizedSubmissionBaseForm
from extrequests.models import SelfOrganizedSubmission
from workshops.models import (
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


class TestSelfOrganizedSubmissionBaseForm(FormTestHelper, TestBase):
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
            'language':  Language.objects.get(name='English').pk,
            'public_event': 'closed',
            'public_event_other': '',
            'additional_contact': '',
            'data_privacy_agreement': True,
            'code_of_conduct_agreement': True,
            'host_responsibilities': True,
        }

    def test_minimal_form(self):
        """Test if minimal form works."""
        data = self.minimal_data.copy()
        form = SelfOrganizedSubmissionBaseForm(data)
        self.assertTrue(form.is_valid(), dict(form.errors))

    def test_institution_validation(self):
        """Make sure institution data is present, and validation
        errors are triggered for various matrix of input data."""

        # 1: selected institution from the list
        data = {
            'institution': Organization.objects
                                       .exclude(fullname='self-organized')
                                       .first().pk,
            'institution_other_name': '',
            'institution_other_URL': '',
            'institution_department': 'School of Wizardry',
        }
        form = SelfOrganizedSubmissionBaseForm(data)
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
        form = SelfOrganizedSubmissionBaseForm(data)
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
        form = SelfOrganizedSubmissionBaseForm(data)
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
        form = SelfOrganizedSubmissionBaseForm(data)
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
        form = SelfOrganizedSubmissionBaseForm(data)
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
        form = SelfOrganizedSubmissionBaseForm(data)
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
        form = SelfOrganizedSubmissionBaseForm(data)
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
        form = SelfOrganizedSubmissionBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertIn('institution_other_name', form.errors)
        self.assertIn('institution_other_URL', form.errors)
        self.assertNotIn('institution_department', form.errors)

    def test_workshop_URL(self):
        """Test validation of workshop URL."""
        # 1: required only when workshop format is "standard" 2-day workshop
        data = self.minimal_data.copy()
        data['workshop_format'] = 'short'
        form = SelfOrganizedSubmissionBaseForm(data)
        self.assertNotIn('workshop_format', form.errors)
        self.assertNotIn('workshop_url', form.errors)

        data['workshop_format'] = 'standard'
        form = SelfOrganizedSubmissionBaseForm(data)
        self.assertNotIn('workshop_format', form.errors)
        self.assertIn('workshop_url', form.errors)

        data['workshop_url'] = 'https://github.com/'
        form = SelfOrganizedSubmissionBaseForm(data)
        self.assertNotIn('workshop_format', form.errors)
        self.assertNotIn('workshop_url', form.errors)

        # 2: wrong URL
        data = self.minimal_data.copy()
        data['workshop_url'] = 'not_an_URL'
        form = SelfOrganizedSubmissionBaseForm(data)
        self.assertIn('workshop_url', form.errors)

    def test_workshop_format(self):
        """Test validation of workshop format."""
        self._test_field_other(
            Form=SelfOrganizedSubmissionBaseForm,
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
        form = SelfOrganizedSubmissionBaseForm(data)
        self.assertNotIn('workshop_types', form.errors)
        self.assertNotIn('workshop_types_other_explain', form.errors)

        # 2: error when mix&match but no explanation
        data = self.minimal_data.copy()
        data['workshop_types'] = [curricula.filter(mix_match=True).first().pk]
        data['workshop_types_other_explain'] = ""
        form = SelfOrganizedSubmissionBaseForm(data)
        self.assertNotIn('workshop_types', form.errors)
        self.assertIn('workshop_types_other_explain', form.errors)

        # 3: error fixed
        data = self.minimal_data.copy()
        data['workshop_types'] = [curricula.filter(mix_match=True).first().pk]
        data['workshop_types_other_explain'] = ("It does matter when "
                                                "mix&match is selected.")
        form = SelfOrganizedSubmissionBaseForm(data)
        self.assertNotIn('workshop_types', form.errors)
        self.assertNotIn('workshop_types_other_explain', form.errors)

    def test_public_event(self):
        """Test validation of event's openness to public."""
        self._test_field_other(
            Form=SelfOrganizedSubmissionBaseForm,
            first_name='public_event',
            other_name='public_event_other',
            valid_first='public',
            valid_other='Open to conference attendees',
            first_when_other="other",
        )


class TestSelfOrganizedSubmissionViews(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()

        self.sos1 = SelfOrganizedSubmission.objects.create(
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

        self.sos2 = SelfOrganizedSubmission.objects.create(
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
        rv = self.client.get(reverse('all_selforganizedsubmissions'))
        self.assertIn(self.sos1, rv.context['submissions'])
        self.assertNotIn(self.sos2, rv.context['submissions'])

    def test_discarded_requests_list(self):
        rv = self.client.get(reverse('all_selforganizedsubmissions') + '?state=d')
        self.assertNotIn(self.sos1, rv.context['submissions'])
        self.assertIn(self.sos2, rv.context['submissions'])

    def test_set_state_pending_request_view(self):
        rv = self.client.get(reverse('selforganizedsubmission_set_state',
                                     args=[self.sos1.pk, 'discarded']))
        self.assertEqual(rv.status_code, 302)
        self.sos1.refresh_from_db()
        self.assertEqual(self.sos1.state, "d")

    def test_set_state_discarded_request_view(self):
        rv = self.client.get(reverse('selforganizedsubmission_set_state',
                                     args=[self.sos2.pk, 'discarded']))
        self.assertEqual(rv.status_code, 302)
        self.sos2.refresh_from_db()
        self.assertEqual(self.sos2.state, "d")

    def test_pending_request_accept(self):
        rv = self.client.get(reverse('selforganizedsubmission_set_state',
                                     args=[self.sos1.pk, 'accepted']))
        self.assertEqual(rv.status_code, 302)

    def test_pending_request_accepted_with_event(self):
        """Ensure a backlink from Event to SelfOrganizedSubmission that created
        the event exists after ER is accepted."""
        data = {
            'slug': '2018-10-28-test-event',
            'host': Organization.objects.first().pk,
            'tags': [1],
            'invoice_status': 'unknown',
        }
        rv = self.client.post(
            reverse('selforganizedsubmission_accept_event',
                    args=[self.sos1.pk]),
            data)
        self.assertEqual(rv.status_code, 302)
        request = Event.objects.get(slug='2018-10-28-test-event') \
                               .selforganizedsubmission
        self.assertEqual(request, self.sos1)

    def test_lessons_shown_in_event_create_form(self):
        """Ensure Mix&Match triggers "lessons" field on EventCreateForm."""
        # self.sos1 has Mix&Match workshop type, so it should display "lessons"
        # field in Event form
        url = reverse('selforganizedsubmission_accept_event',
                      args=[self.sos1.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)
        self.assertIn(Curriculum.objects.get(mix_match=True),
                      self.sos1.workshop_types.all())
        self.assertIn("lessons", rv.context["form"].fields.keys())

        # self.sos2 doesn't have Mix&Match workshop type, so it can't show
        # "lessons" field in Event form
        # but for tests we need a different status for that submission
        self.sos2.state = "p"
        self.sos2.save()
        url = reverse('selforganizedsubmission_accept_event',
                      args=[self.sos2.pk])
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)
        self.assertNotIn(Curriculum.objects.get(mix_match=True),
                         self.sos2.workshop_types.all())
        self.assertNotIn("lessons", rv.context["form"].fields.keys())

    def test_discarded_request_accepted_with_event(self):
        rv = self.client.get(reverse('selforganizedsubmission_accept_event',
                                     args=[self.sos2.pk]))
        self.assertEqual(rv.status_code, 404)

    def test_pending_request_discard(self):
        rv = self.client.get(reverse('selforganizedsubmission_set_state',
                                     args=[self.sos1.pk, 'discarded']),
                             follow=True)
        self.assertEqual(rv.status_code, 200)

    def test_discarded_request_discard(self):
        rv = self.client.get(reverse('selforganizedsubmission_set_state',
                                     args=[self.sos2.pk, 'discarded']),
                             follow=True)
        self.assertEqual(rv.status_code, 200)

    def test_discarded_request_reopened(self):
        self.sos1.state = "a"
        self.sos1.save()
        self.client.get(
            reverse('selforganizedsubmission_set_state',
                    args=[self.sos1.pk, 'pending']),
            follow=True)
        self.sos1.refresh_from_db()
        self.assertEqual(self.sos1.state, "p")

    def test_accepted_request_reopened(self):
        self.assertEqual(self.sos2.state, "d")
        self.client.get(
            reverse('selforganizedsubmission_set_state',
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

        rv = self.client.get(reverse('all_selforganizedsubmissions'))

        # some objects available in the page
        self.assertNotEqual(len(rv.context['submissions']), 0)

        # no string_if_invalid found in the page
        invalid = settings.TEMPLATES[0]['OPTIONS']['string_if_invalid']
        self.assertNotIn(invalid, rv.content.decode('utf-8'))

    def test_host_task_created(self):
        """Ensure a host task is created when a person submitting already is in
        our database."""

        # Harry matched as a submitted for self.sos1, and he has no tasks so far
        self.assertEqual(self.sos1.host(), self.harry)
        self.assertFalse(self.harry.task_set.all())

        # create event from that workshop inquiry
        data = {
            'slug': '2019-08-18-test-event',
            'host': Organization.objects.first().pk,
            'tags': [1],
        }
        rv = self.client.post(
            reverse('selforganizedsubmission_accept_event',
                    args=[self.sos1.pk]),
            data)
        self.assertEqual(rv.status_code, 302)
        event = Event.objects.get(slug='2019-08-18-test-event')

        # check if Harry gained a task
        Task.objects.get(person=self.harry, event=event,
                         role=Role.objects.get(name="host"))
