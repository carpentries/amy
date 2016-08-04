from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.template import Context
from django.template import Template

from .base import TestBase
from ..models import (
    Person,
    Role,
    TrainingRequest,
    Organization,
    Event,
    Tag,
    Task,
)


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
            'recaptcha_response_field': 'PASSED',
        }
        rv = self.client.post(reverse('training_request'), data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self._save_html(content)
        self.assertNotIn('Fix errors below', content)
        self.assertEqual(TrainingRequest.objects.all().count(), 1)


def create_training_request(state, person):
    return TrainingRequest.objects.create(
        personal='John',
        family='Smith',
        email='john@smith.com',
        occupation='',
        affiliation='AGH University of Science and Technology',
        location='Cracow',
        country='PL',
        gender=Person.MALE,
        previous_training='none',
        previous_experience='none',
        programming_language_usage_frequency='daily',
        reason='Just for fun.',
        teaching_frequency_expectation='often',
        max_travelling_frequency='yearly',
        state=state,
        person=person,
    )


class TestTrainingRequestModel(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

    def test_valid_pending_request(self):
        req = create_training_request(state='p', person=None)
        req.full_clean()

    def test_valid_accepted_request(self):
        req = create_training_request(state='a', person=self.admin)
        req.full_clean()

    def test_pending_request_must_not_be_matched(self):
        req = create_training_request(state='p', person=self.admin)
        with self.assertRaises(ValidationError):
            req.full_clean()

    def test_accepted_request_must_be_matched_to_a_trainee(self):
        req = create_training_request(state='a', person=None)
        with self.assertRaises(ValidationError):
            req.full_clean()


class TestTrainingRequestsListView(TestBase):
    def setUp(self):
        self._setUpRoles()
        self._setUpUsersAndLogin()

        self.req = TrainingRequest.objects.create(
            personal='John',
            family='Smith',
            email='john@smith.com',
            occupation='',
            affiliation='AGH University of Science and Technology',
            location='Cracow',
            country='PL',
            gender=Person.MALE,
            previous_training='none',
            previous_experience='none',
            programming_language_usage_frequency='daily',
            reason='Just for fun.',
            teaching_frequency_expectation='often',
            max_travelling_frequency='yearly',
        )
        self.req.previous_involvement.add(Role.objects.get(name='host'))
        self.req.save()

    def test_list_view(self):
        rv = self.client.get(reverse('all_trainingrequests'))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(list(rv.context['requests']), [self.req])

    def test_detailed_view(self):
        rv = self.client.get(reverse('trainingrequest_details',
                                     args=[self.req.pk]))
        self.assertEqual(rv.status_code, 200)
