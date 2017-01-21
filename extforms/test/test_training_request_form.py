from django.core.urlresolvers import reverse

from workshops.models import Person, Role, TrainingRequest
from workshops.test import TestBase


class TestTrainingRequestForm(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpRoles()

    def test_request_added(self):
        data = {
            'group': 'coolprogrammers',
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
            'gender': Person.MALE,
            'gender_other': '',
            'previous_involvement': [Role.objects.get(name='host').id],
            'previous_training': 'none',
            'previous_training_other': '',
            'previous_training_explanation': '',
            'previous_experience': 'none',
            'previous_experience_other': '',
            'previous_experience_explanation': '',
            'programming_language_usage_frequency': 'daily',
            'reason': 'Just for fun.',
            'teaching_frequency_expectation': 'often',
            'teaching_frequency_expectation_other': '',
            'max_travelling_frequency': 'yearly',
            'max_travelling_frequency_other': '',
            'addition_skills': '',
            'comment': '',
            'agreed_to_code_of_conduct': 'on',
            'agreed_to_complete_training': 'on',
            'agreed_to_teach_workshops': 'on',
            'privacy_consent': True,
            'recaptcha_response_field': 'PASSED',
        }
        rv = self.client.post(reverse('training_request'), data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self._save_html(content)
        self.assertNotIn('Fix errors below', content)
        self.assertEqual(TrainingRequest.objects.all().count(), 1)