from django.core import mail
from django.urls import reverse

from .base import TestBase
from ..forms import DCSelfOrganizedEventRequestForm
from ..models import (
    DCSelfOrganizedEventRequest,
    DCWorkshopDomain,
    DCWorkshopTopic,
    AcademicLevel,
    DataAnalysisLevel,
)


class TestDCSelfOrganizedEventRequestForm(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self.request = DCSelfOrganizedEventRequest.objects.create(
            name='Harry Potter', email='harry@potter.com',
            organization='Hogwarts School of Witchcraft and Wizardry',
            is_partner='y', instructor_status='both',
            location='Scotland', country='GB',
            dates='2016-06-18 to 2016-06-19',
            payment='invoice', handle_registration=True,
            distribute_surveys=True, follow_code_of_conduct=True,
        )
        self.request.domains.add(*DCWorkshopDomain.objects.all()[0:2])
        self.request.topics.add(*DCWorkshopTopic.objects.all()[0:2])
        self.request.attendee_academic_levels.add(
            AcademicLevel.objects.first())
        self.request.attendee_data_analysis_level.add(
            DataAnalysisLevel.objects.first())

    def test_exact_fields(self):
        """Test if the form shows correct fields."""
        form = DCSelfOrganizedEventRequestForm()
        fields_left = list(form.fields.keys())
        fields_right = [
            'name', 'email', 'organization', 'instructor_status', 'is_partner',
            'is_partner_other', 'location', 'country', 'associated_conference',
            'dates', 'domains', 'domains_other', 'topics', 'topics_other',
            'attendee_academic_levels', 'attendee_data_analysis_level',
            'payment', 'fee_waiver_reason', 'handle_registration',
            'distribute_surveys', 'follow_code_of_conduct', 'privacy_consent',
            'captcha',
        ]
        self.assertEqual(fields_left, fields_right)

    def test_submission_added(self):
        """Test if the submitted form adds a new event submission."""
        self.assertEqual(len(DCSelfOrganizedEventRequest.objects.all()), 1)
        data = {
            'g-recaptcha-response': 'PASSED',
            'name': 'Harry Potter',
            'email': 'harry@potter.com',
            'organization': 'Hogwarts School of Witchcraft and Wizardry',
            'is_partner': 'y',
            'instructor_status': 'both',
            'location': 'Scotland',
            'country': 'GB',
            'dates': '2016-06-18 to 2016-06-19',
            'payment': 'invoice',
            'handle_registration': True,
            'distribute_surveys': True,
            'follow_code_of_conduct': True,
            'domains': DCWorkshopDomain.objects
                                       .values_list('pk', flat=True)[0:2],
            'topics': DCWorkshopTopic.objects
                                     .values_list('pk', flat=True)[0:2],
            'attendee_academic_levels': [AcademicLevel.objects.first().pk],
            'attendee_data_analysis_level':
                [DataAnalysisLevel.objects.first().pk],
            'privacy_consent': True,
        }
        rv = self.client.post(reverse('dc_workshop_selforganized_request'),
                              data, follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertNotIn('form', rv.context)
        self.assertEqual(len(DCSelfOrganizedEventRequest.objects.all()), 2)

    def test_submission_sends_email(self):
        """Test if the submitted form results in email sent."""
        data = {
            'g-recaptcha-response': 'PASSED',
            'name': 'Harry Potter',
            'email': 'harry@potter.com',
            'organization': 'Hogwarts School of Witchcraft and Wizardry',
            'is_partner': 'y',
            'instructor_status': 'both',
            'location': 'Scotland',
            'country': 'GB',
            'dates': '2016-06-18 to 2016-06-19',
            'payment': 'invoice',
            'handle_registration': True,
            'distribute_surveys': True,
            'follow_code_of_conduct': True,
            'domains': DCWorkshopDomain.objects
                                       .values_list('pk', flat=True)[0:2],
            'topics': DCWorkshopTopic.objects
                                     .values_list('pk', flat=True)[0:2],
            'attendee_academic_levels': [AcademicLevel.objects.first().pk],
            'attendee_data_analysis_level':
                [DataAnalysisLevel.objects.first().pk],
            'privacy_consent': True,
        }
        rv = self.client.post(reverse('dc_workshop_selforganized_request'),
                              data, follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertNotIn('form', rv.context)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(
            msg.subject,
            'DC: new self-organized workshop request from {} @ {}'.format(
                'Harry Potter', 'Hogwarts School of Witchcraft and Wizardry')
        )
