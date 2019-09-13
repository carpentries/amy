from django.core import mail
from django.conf import settings
from django.urls import reverse

from extforms.forms import SelfOrganisedSubmissionExternalForm
from extrequests.models import SelfOrganisedSubmission
from workshops.models import (
    Language,
    AcademicLevel,
    ComputingExperienceLevel,
    Curriculum,
    InfoSource,
)
from workshops.tests.base import TestBase


class TestSelfOrganisedSubmissionExternalForm(TestBase):
    """Test external (accessible to non-logged in users) form."""

    def test_fields_presence(self):
        """Test if the form shows correct fields."""
        form = SelfOrganisedSubmissionExternalForm()
        fields_left = set(form.fields.keys())
        fields_right = set([
            "personal", "family", "email",
            "institution", "institution_other_name", "institution_other_URL",
            "institution_department",
            "workshop_format", "workshop_format_other",
            "workshop_url",
            "workshop_types", "workshop_types_other_explain",
            "country", "language",
            "public_event", "public_event_other",
            "additional_contact",
            "data_privacy_agreement", "code_of_conduct_agreement",
            "host_responsibilities",
            "captcha",
        ])
        self.assertEqual(fields_left, fields_right)

    def test_request_added(self):
        """Ensure the request is successfully added to the pool, and
        notification email is sent."""
        data = {
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
        }
        self.passCaptcha(data)

        rv = self.client.post(reverse('selforganised_submission'), data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        if 'form' in rv.context:
            self.assertEqual(rv.context['form'].is_valid(), True,
                             dict(rv.context['form'].errors))
        self.assertNotIn('Please fix errors in the form below', content)
        self.assertIn('Thank you for submitting self-organised workshop',
                      content)
        self.assertEqual(SelfOrganisedSubmission.objects.all().count(), 1)
        self.assertEqual(SelfOrganisedSubmission.objects.all()[0].state, 'p')

        # 1 email for autoresponder, 1 email for admins
        self.assertEqual(len(mail.outbox), 2)

        # save the email messages for test debuggig
        # with open('email0.eml', 'wb') as f:
        #     f.write(mail.outbox[0].message().as_bytes())
        # with open('email1.eml', 'wb') as f:
        #     f.write(mail.outbox[1].message().as_bytes())

        # before tests, check if the template invalid string exists
        self.assertTrue(settings.TEMPLATES[0]['OPTIONS']['string_if_invalid'])

        # test autoresponder email
        msg = mail.outbox[0]
        self.assertEqual(msg.subject, 'Self-organised submission confirmation')
        self.assertEqual(msg.recipients(), ['hpotter@magic.gov'])
        self.assertNotIn(settings.TEMPLATES[0]['OPTIONS']['string_if_invalid'],
                         msg.body)
        # test email for admins
        msg = mail.outbox[1]
        self.assertEqual(
            msg.subject,
            'New self-organised submission: Ministry of Magic',
        )
        self.assertEqual(msg.recipients(), ['admin-uk@carpentries.org'])
        self.assertNotIn(settings.TEMPLATES[0]['OPTIONS']['string_if_invalid'],
                         msg.body)
