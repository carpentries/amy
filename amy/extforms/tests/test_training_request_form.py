from django.core import mail
from django.urls import reverse
from webtest import forms

from extforms.views import TrainingRequestCreate
from workshops.models import Role, TrainingRequest
from workshops.tests.base import TestBase


class TestTrainingRequestForm(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self.data = {
            'review_process': 'preapproved',
            'group_name': 'coolprogrammers',
            'personal': 'John',
            'family': 'Smith',
            'email': 'john@smith.com',
            'github': '',
            'occupation': '',
            'occupation_other': 'unemployed',
            'affiliation': 'AGH University of Science and Technology',
            'location': 'Cracow',
            'country': 'PL',
            'domains': [1, 2],
            'domains_other': '',
            'underrepresented': 'undisclosed',
            'previous_involvement': [Role.objects.get(name='host').id],
            'previous_training': 'none',
            'previous_training_other': '',
            'previous_training_explanation': '',
            'previous_experience': 'none',
            'previous_experience_other': '',
            'previous_experience_explanation': '',
            'programming_language_usage_frequency': 'daily',
            'reason': 'Just for fun.',
            'teaching_frequency_expectation': 'monthly',
            'teaching_frequency_expectation_other': '',
            'max_travelling_frequency': 'yearly',
            'max_travelling_frequency_other': '',
            'addition_skills': '',
            'user_notes': '',
            'agreed_to_code_of_conduct': 'on',
            'agreed_to_complete_training': 'on',
            'agreed_to_teach_workshops': 'on',
            'privacy_consent': True,
        }

    def test_request_added(self):
        email = 'john@smith.com'
        self.passCaptcha(self.data)

        rv = self.client.post(reverse('training_request'), self.data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self.assertNotIn('fix errors in the form below', content)
        self.assertEqual(TrainingRequest.objects.all().count(), 1)

        # Test that the sender was emailed
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [email])
        self.assertEqual(msg.subject,
                         TrainingRequestCreate.autoresponder_subject)
        self.assertIn('A copy of your request', msg.body)
        # with open('email.eml', 'wb') as f:
        #     f.write(msg.message().as_bytes())

    def test_review_process_validation(self):
        # 1: shouldn't pass when review_process requires group_name
        self.data['review_process'] = 'preapproved'
        self.data['group_name'] = ''
        self.passCaptcha(self.data)

        rv = self.client.post(reverse('training_request'), self.data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self.assertIn('fix errors in the form below', content)
        self.assertEqual(TrainingRequest.objects.all().count(), 0)

        # 2: shouldn't pass when review_process requires *NO* group_name
        self.data['review_process'] = 'open'
        self.data['group_name'] = 'some_code'
        self.passCaptcha(self.data)

        rv = self.client.post(reverse('training_request'), self.data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self.assertIn('fix errors in the form below', content)
        self.assertEqual(TrainingRequest.objects.all().count(), 0)
