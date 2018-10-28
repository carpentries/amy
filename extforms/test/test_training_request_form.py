from django.urls import reverse

from workshops.models import Person, Role, TrainingRequest
from workshops.test import TestBase


class TestTrainingRequestForm(TestBase):
    def setUp(self):
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
            'underrepresented': '',
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
            'comment': '',
            'agreed_to_code_of_conduct': 'on',
            'agreed_to_complete_training': 'on',
            'agreed_to_teach_workshops': 'on',
            'privacy_consent': True,
        }
        self.passCaptcha(data)

        rv = self.client.post(reverse('training_request'), data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self._save_html(content)
        self.assertNotIn('Fix errors below', content)
        self.assertEqual(TrainingRequest.objects.all().count(), 1)


class GroupNameFieldTestsBase(TestBase):
    """Tests for [#1005] feature -- Allow pre-population of Group in training
    request form.

    [#1005]: https://github.com/swcarpentry/amy/issues/1005"""

    url_suffix = ''

    def setUp(self):
        url = reverse('training_request') + self.url_suffix
        self.form = self.app.get(url).form

    def fillin_and_submit(self):
        # fillin the form
        self.form['personal'] = 'John'
        self.form['family'] = 'Smith'
        self.form['email'] = 'john@smith.com'
        self.form['affiliation'] = 'AGH University of Science and Technology'
        self.form['location'] = 'Cracow'
        self.form['country'] = 'PL'
        self.form['reason'] = 'Just for fun.'
        self.form['data_privacy_agreement'] = True
        self.form['code_of_conduct_agreement'] = True
        self.form['training_completion_agreement'] = True
        self.form['workshop_teaching_agreement'] = True
        self.form['g-recaptcha-response'] = 'PASSED'

        # submit the form
        self.rs = self.form.submit().maybe_follow()

    def assertSubmissionIsRecorded(self, with_group_name):
        # the form should be successfully submitted
        self.assertEqual(self.rs.status_code, 200)

        # submission should be recorded
        self.assertEqual(TrainingRequest.objects.count(), 1)

        # with right group name
        request = TrainingRequest.objects.first()
        self.assertEqual(request.group_name, with_group_name)


class WhenGroupNameIsPrefilledIn(GroupNameFieldTestsBase):
    url_suffix = '?group=asdf qwer'

    def test_then_the_group_name_field_should_be_not_displayed(self):
        self.assertEqual(self.form['group_name'].attrs.get('type'), 'hidden')

    def test_then_the_prefilled_in_value_should_be_used(self):
        self.fillin_and_submit()
        self.assertSubmissionIsRecorded(with_group_name='asdf qwer')


class WhenNoGroupNameIsPrefilledIn(GroupNameFieldTestsBase):
    url_suffix = ''

    def test_group_field_should_be_displayed(self):
        self.assertNotEqual(self.form['group_name'].attrs.get('type'), 'hidden')

    def test_group_name_field_should_be_optional(self):
        self.fillin_and_submit()
        self.assertSubmissionIsRecorded(with_group_name='')

    def test_group_name_provided_by_user_should_be_used(self):
        self.form['group_name'] = 'asdf'
        self.fillin_and_submit()
        self.assertSubmissionIsRecorded(with_group_name='asdf')


class WhenEmptyGroupNameIsPrefilledIn(WhenNoGroupNameIsPrefilledIn):
    url_suffix = '?group='
