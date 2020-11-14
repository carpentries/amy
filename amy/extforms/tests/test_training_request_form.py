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
        if self.form['group_name'].value:
            self.form['review_process'] = 'preapproved'
        else:
            self.form['review_process'] = 'open'
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
        # g-recaptcha-response doesn't exist in the form, so this tricks the webtest
        # form by adding the non-existing field to it
        field = forms.Text(self.form, 'input', 'g-recaptcha-response', 0, 'PASSED')
        self.form.fields['g-recaptcha-response'] = field
        self.form.field_order.append(('g-recaptcha-response', field))

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
        self.assertNotEqual(self.form['group_name'].attrs.get('type'),
                            'hidden')

    def test_group_name_field_should_be_optional(self):
        self.fillin_and_submit()
        self.assertSubmissionIsRecorded(with_group_name='')

    def test_group_name_provided_by_user_should_be_used(self):
        self.form['group_name'] = 'asdf'
        self.fillin_and_submit()
        self.assertSubmissionIsRecorded(with_group_name='asdf')


class WhenEmptyGroupNameIsPrefilledIn(WhenNoGroupNameIsPrefilledIn):
    url_suffix = '?group='
