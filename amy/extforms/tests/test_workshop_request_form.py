from django.core import mail
from django.urls import reverse

from extforms.forms import WorkshopRequestExternalForm
from workshops.models import (
    Language,
    AcademicLevel,
    ComputingExperienceLevel,
    Curriculum,
    WorkshopRequest,
)
from workshops.tests import TestBase


class TestWorkshopRequestExternalForm(TestBase):
    """Test external (accessible to non-logged in users) form."""

    def test_fields_presence(self):
        """Test if the form shows correct fields."""
        form = WorkshopRequestExternalForm()
        fields_left = set(form.fields.keys())
        fields_right = set([
            "personal", "family", "email", "institution", "institution_name",
            "institution_department", "location", "country",
            "part_of_conference", "conference_details", "preferred_dates",
            "language", "number_attendees", "domains", "domains_other",
            "academic_levels", "computing_levels", "audience_description",
            "requested_workshop_types", "organization_type",
            "self_organized_github", "centrally_organized_fee",
            "waiver_circumstances", "travel_expences_agreement",
            "travel_expences_management", "travel_expences_management_other",
            "comment", "data_privacy_agreement", "code_of_conduct_agreement",
            "host_responsibilities", "captcha",
        ])
        self.assertEqual(fields_left, fields_right)

    def test_request_added(self):
        """Ensure the request is successfully added to the pool, and
        notification email is sent."""
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
                Curriculum.objects.get(slug='swc-python').pk,
                Curriculum.objects.get(slug='dc-ecology-r').pk,
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
        self.passCaptcha(data)

        rv = self.client.post(reverse('workshop_request'), data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        if 'form' in rv.context:
            self.assertEqual(rv.context['form'].is_valid(), True,
                             dict(rv.context['form'].errors))
        self.assertNotIn('Please fix errors in the form below', content)
        self.assertIn('Thank you for requesting a workshop', content)
        self.assertEqual(WorkshopRequest.objects.all().count(), 1)
        self.assertEqual(WorkshopRequest.objects.all()[0].state, 'p')
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(
            msg.subject,
            'New workshop request: Ministry of Magic, 03-04 November, 2018',
        )
        self.assertEqual(msg.recipients(), ['admin-uk@carpentries.org'])
