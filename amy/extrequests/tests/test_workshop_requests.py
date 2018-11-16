from django.urls import reverse

from extrequests.forms import WorkshopRequestBaseForm
from workshops.models import (
    WorkshopRequest,
    Event,
    Organization,
    Language,
    KnowledgeDomain,
    AcademicLevel,
    ComputingExperienceLevel,
    Curriculum,
)
from workshops.tests.base import TestBase


class TestWorkshopRequestBaseForm(TestBase):
    """Test base form validation."""

    def test_minimal_form(self):
        """Test if minimal form works."""
        data = {
            'personal': 'Harry',
            'family': 'Potter',
            'email': 'hpotter@magic.gov',
            'institution_name': 'Ministry of Magic',
            'location': 'London',
            'country': 'GB',
            'preferred_dates': '03-04 November, 2018',
            'language':  Language.objects.get(name='English').pk,
            'number_attendees': '10-40',
            'domains': [],
            'domains_other': 'Wizardry',
            'academic_levels': [AcademicLevel.objects.first().pk],
            'computing_levels': [ComputingExperienceLevel.objects.first().pk],
            'audience_description': 'Students of Hogwarts',
            'requested_workshop_types': [
                Curriculum.objects.first().pk,
            ],
            'organization_type': 'central',
            'self_organized_github': '',
            'centrally_organized_fee': 'waiver',
            'waiver_circumstances': 'Bugdet cuts in Ministry of Magic',
            'travel_expences_agreement': True,
            'travel_expences_management': 'booked',
            'travel_expences_management_other': '',
            'comment': 'N/c',
            'data_privacy_agreement': True,
            'code_of_conduct_agreement': True,
            'host_responsibilities': True,
        }
        form = WorkshopRequestBaseForm(data)
        self.assertTrue(form.is_valid(), dict(form.errors))

    def test_institution_validation(self):
        """Make sure some institution data is present, and validation
        errors are triggered for various matrix of input data."""

        # 1: selected institution from the list
        data = {
            'institution': Organization.objects.first().pk,
            'institution_name': '',
            'institution_department': 'School of Wizardry',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertNotIn('institution_name', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 2: institution name manually entered
        data = {
            'institution': '',
            'institution_name': 'Hogwarts',
            'institution_department': 'School of Wizardry',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertNotIn('institution_name', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 3: no institution and no department
        data = {
            'institution': '',
            'institution_name': '',
            'institution_department': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertIn('institution', form.errors)  # institution is required
        self.assertNotIn('institution_name', form.errors)
        self.assertNotIn('institution_department', form.errors)

        # 4: no institution, but department selected
        data = {
            'institution': '',
            'institution_name': '',
            'institution_department': 'School of Wizardry',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertIn('institution', form.errors)  # institution is required
        self.assertNotIn('institution_name', form.errors)
        # institution is required for not-empty department
        self.assertIn('institution_department', form.errors)

        # 5: both institution and institution_name filled
        data = {
            'institution': Organization.objects.first().pk,
            'institution_name': 'Hogwarts',
            'institution_department': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('institution', form.errors)
        self.assertIn('institution_name', form.errors)  # can't use both fields
        self.assertNotIn('institution_department', form.errors)

    def test_conference_validation(self):
        """Ensure correct validation for conference details."""

        # 1: no conference
        data = {
            'part_of_conference': False,
            'conference_details': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('part_of_conference', form.errors)
        self.assertNotIn('conference_details', form.errors)

        # 2: correct conference data
        data = {
            'part_of_conference': True,
            'conference_details': 'PyCon 2019',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('part_of_conference', form.errors)
        self.assertNotIn('conference_details', form.errors)

        # 3: part of conference and missing conference details
        data = {
            'part_of_conference': True,
            'conference_details': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('part_of_conference', form.errors)
        self.assertIn('conference_details', form.errors)

        # 4: conference details, but missing part of conference field
        data = {
            'part_of_conference': False,
            'conference_details': 'PyCon 2019',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('part_of_conference', form.errors)
        self.assertIn('conference_details', form.errors)

    def test_organization_type(self):
        """Test validation of fields related to values in
        `organization_type`."""

        # 1: valid self-organized
        data = {
            'organization_type': 'self',
            'self_organized_github':
                'http://hogwarts.github.io/2018-11-03-Hogwarts',
            'centrally_organized_fee': 'nonprofit',  # needs to be present
            'waiver_circumstances': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('organization_type', form.errors)
        self.assertNotIn('self_organized_github', form.errors)
        self.assertNotIn('centrally_organized_fee', form.errors)
        self.assertNotIn('waiver_circumstances', form.errors)

        # 2: valid centrally-organized (no waiver)
        data = {
            'organization_type': 'central',
            'self_organized_github': '',
            'centrally_organized_fee': 'nonprofit',
            'waiver_circumstances': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('organization_type', form.errors)
        self.assertNotIn('self_organized_github', form.errors)
        self.assertNotIn('centrally_organized_fee', form.errors)
        self.assertNotIn('waiver_circumstances', form.errors)

        # 3: valid centrally-organized (with waiver)
        data = {
            'organization_type': 'central',
            'self_organized_github': '',
            'centrally_organized_fee': 'waiver',
            'waiver_circumstances': "We're cheap",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('organization_type', form.errors)
        self.assertNotIn('self_organized_github', form.errors)
        self.assertNotIn('centrally_organized_fee', form.errors)
        self.assertNotIn('waiver_circumstances', form.errors)

        # 4: URL required for self-organized workshop type
        data = {
            'organization_type': 'self',
            'self_organized_github': '',
            'centrally_organized_fee': 'nonprofit',  # field is required
            'waiver_circumstances': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('organization_type', form.errors)
        self.assertIn('self_organized_github', form.errors)
        self.assertNotIn('centrally_organized_fee', form.errors)
        self.assertNotIn('waiver_circumstances', form.errors)

        # 5: fee required for centrally-organized workshop type
        data = {
            'organization_type': 'central',
            'self_organized_github': '',
            'centrally_organized_fee': '',
            'waiver_circumstances': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('organization_type', form.errors)
        self.assertNotIn('self_organized_github', form.errors)
        self.assertIn('centrally_organized_fee', form.errors)
        self.assertNotIn('waiver_circumstances', form.errors)

        # 6: waiver circumstances explanation required for centrally-organized
        #    workshop type with waiver request
        data = {
            'organization_type': 'central',
            'self_organized_github': '',
            'centrally_organized_fee': 'waiver',
            'waiver_circumstances': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('organization_type', form.errors)
        self.assertNotIn('self_organized_github', form.errors)
        self.assertNotIn('centrally_organized_fee', form.errors)
        self.assertIn('waiver_circumstances', form.errors)

        # 7: special case - someone left garbage in URL field, but selected
        #    centrally-organized workshop type; in this case URL field contents
        #    is not removed, and shows up in errors
        data = {
            'organization_type': 'central',
            'self_organized_github': 'not-a-real-URL',
            'centrally_organized_fee': 'nonprofit',
            'waiver_circumstances': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('organization_type', form.errors)
        self.assertIn('self_organized_github', form.errors)
        self.assertNotIn('centrally_organized_fee', form.errors)
        self.assertNotIn('waiver_circumstances', form.errors)

        # 8: missing organization type
        data = {
            'organization_type': '',
            'centrally_organized_fee': 'nonprofit',  # field is required
        }
        form = WorkshopRequestBaseForm(data)
        self.assertIn('organization_type', form.errors)
        self.assertNotIn('self_organized_github', form.errors)
        self.assertNotIn('centrally_organized_fee', form.errors)
        self.assertNotIn('waiver_circumstances', form.errors)

    def test_domains(self):
        """Test validation of domains."""

        # 1: data required
        data = {
            'domains': [],
            'domains_other': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertIn('domains', form.errors)
        self.assertNotIn('domains_other', form.errors)

        # 2: valid entry (domains only)
        data = {
            'domains': [KnowledgeDomain.objects.first().pk],
            'domains_other': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('domains', form.errors)
        self.assertNotIn('domains_other', form.errors)

        # 3: valid entry (domains_other only)
        data = {
            'domains': [],
            'domains_other': 'Wizardry',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('domains', form.errors)
        self.assertNotIn('domains_other', form.errors)

    def test_travel_expences_management(self):
        """Test validation of travel expences management."""

        # 1: data required
        data = {
            'travel_expences_management': '',
            'travel_expences_management_other': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertIn('travel_expences_management', form.errors)
        self.assertNotIn('travel_expences_management_other', form.errors)

        # 2: valid entry (travel_expences_management only)
        data = {
            'travel_expences_management': 'reimbursed',
            'travel_expences_management_other': '',
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('travel_expences_management', form.errors)
        self.assertNotIn('travel_expences_management_other', form.errors)

        # 3: valid entry (travel_expences_management_other only)
        data = {
            'travel_expences_management': '',
            'travel_expences_management_other':
                "Local instructors don't need reimbursement",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn('travel_expences_management', form.errors)
        self.assertNotIn('travel_expences_management_other', form.errors)

    def test_domains_order_preserved(self):
        """In #1405 it was requested to have "Don't know yet" option always
        last, and other options sorted alphabetically. It posed a serious
        issue, but thankfully since Django 1.8 it's possible with Case(When())
        added to the `.order_by` clause."""
        form = WorkshopRequestBaseForm()
        domains_qs = form.fields['domains'].queryset

        # make sure that "Don't know yet" is last on the list
        self.assertEqual(domains_qs.last(),
                         KnowledgeDomain.objects.get(name="Don't know yet"))

        # make sure other elements on the list [0..-1] are still sorted
        # alphabetically by name
        domain_names = list(domains_qs.values_list('name', flat=True))[:-1]
        self.assertEqual(domain_names, sorted(domain_names))


class TestWorkshopRequestViews(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

        self.wr1 = WorkshopRequest.objects.create(
            state="p", personal="Harry", family="Potter",
            email="harry@potter.com",
            institution_name="Hogwarts", location="Scotland", country="GB",
            part_of_conference=False, preferred_dates="soon",
            language=Language.objects.get(name='English'),
            audience_description="Students of Hogwarts",
            organization_type='self',
        )
        self.wr2 = WorkshopRequest.objects.create(
            state="d", personal="Harry", family="Potter",
            email="harry@potter.com",
            institution_name="Hogwarts", location="Scotland", country="GB",
            part_of_conference=False, preferred_dates="soon",
            language=Language.objects.get(name='English'),
            audience_description="Students of Hogwarts",
            organization_type='central',
        )

    def test_pending_requests_list(self):
        rv = self.client.get(reverse('all_workshoprequests'))
        self.assertIn(self.wr1, rv.context['requests'])
        self.assertNotIn(self.wr2, rv.context['requests'])

    def test_discarded_requests_list(self):
        rv = self.client.get(reverse('all_workshoprequests') + '?state=d')
        self.assertNotIn(self.wr1, rv.context['requests'])
        self.assertIn(self.wr2, rv.context['requests'])

    def test_set_state_pending_request_view(self):
        rv = self.client.get(reverse('workshoprequest_set_state',
                                     args=[self.wr1.pk, 'discarded']))
        self.assertEqual(rv.status_code, 302)
        self.wr1.refresh_from_db()
        self.assertEqual(self.wr1.state, "d")

    def test_set_state_discarded_request_view(self):
        rv = self.client.get(reverse('workshoprequest_set_state',
                                     args=[self.wr2.pk, 'discarded']))
        self.assertEqual(rv.status_code, 302)
        self.wr2.refresh_from_db()
        self.assertEqual(self.wr2.state, "d")

    def test_pending_request_accept(self):
        rv = self.client.get(reverse('workshoprequest_set_state',
                                     args=[self.wr1.pk, 'accepted']))
        self.assertEqual(rv.status_code, 302)

    def test_pending_request_accepted_with_event(self):
        """Ensure a backlink from Event to WorkshopRequest that created the
        event exists after ER is accepted."""
        data = {
            'slug': '2018-10-28-test-event',
            'host': Organization.objects.first().pk,
            'tags': [1],
            'invoice_status': 'unknown',
        }
        rv = self.client.post(
            reverse('workshoprequest_accept_event', args=[self.wr1.pk]),
            data)
        self.assertEqual(rv.status_code, 302)
        request = Event.objects.get(slug='2018-10-28-test-event') \
                               .workshoprequest
        self.assertEqual(request, self.wr1)

    def test_discarded_request_accepted_with_event(self):
        rv = self.client.get(reverse('workshoprequest_accept_event',
                                     args=[self.wr2.pk]))
        self.assertEqual(rv.status_code, 404)

    def test_pending_request_discard(self):
        rv = self.client.get(reverse('workshoprequest_set_state',
                                     args=[self.wr1.pk, 'discarded']),
                             follow=True)
        self.assertEqual(rv.status_code, 200)

    def test_discarded_request_discard(self):
        rv = self.client.get(reverse('workshoprequest_set_state',
                                     args=[self.wr2.pk, 'discarded']),
                             follow=True)
        self.assertEqual(rv.status_code, 200)

    def test_discarded_request_reopened(self):
        self.wr1.state = "a"
        self.wr1.save()
        self.client.get(
            reverse('workshoprequest_set_state',
                    args=[self.wr1.pk, 'pending']),
            follow=True)
        self.wr1.refresh_from_db()
        self.assertEqual(self.wr1.state, "p")

    def test_accepted_request_reopened(self):
        self.assertEqual(self.wr2.state, "d")
        self.client.get(
            reverse('workshoprequest_set_state',
                    args=[self.wr2.pk, 'pending']),
            follow=True)
        self.wr2.refresh_from_db()
        self.assertEqual(self.wr2.state, "p")
