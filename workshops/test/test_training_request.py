from django.core import mail
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
        email = 'john@smith.com'
        data = {
            'group': 'coolprogrammers',
            'personal': 'John',
            'family': 'Smith',
            'email': email,
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
            'data_privacy_agreement': 'on',
            'code_of_conduct_agreement': 'on',
            'training_completion_agreement': 'on',
            'workshop_teaching_agreement': True,
            'recaptcha_response_field': 'PASSED',
        }
        rv = self.client.post(reverse('training_request'), data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode('utf-8')
        self._save_html(content)
        self.assertNotIn('Fix errors below', content)
        self.assertEqual(TrainingRequest.objects.all().count(), 1)

        # Test that the sender was emailed
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [email])


def create_training_request(state, person):
    return TrainingRequest.objects.create(
        personal='John',
        family='Smith',
        email='john@smith.com',
        occupation='',
        affiliation='AGH University of Science and Technology',
        location='Cracow',
        country='PL',
        previous_training='none',
        previous_experience='none',
        programming_language_usage_frequency='daily',
        reason='Just for fun.',
        teaching_frequency_expectation='monthly',
        max_travelling_frequency='yearly',
        state=state,
        person=person,
    )


class TestTrainingRequestModel(TestBase):
    def setUp(self):
        # create admin account
        self._setUpUsersAndLogin()

        # create trainee account
        self._setUpRoles()
        self._setUpTags()

        self.trainee = Person.objects.create_user(
            username='trainee', personal='Bob',
            family='Smith', email='bob@smith.com')
        org = Organization.objects.create(domain='example.com',
                                          fullname='Test Organization')
        training = Event.objects.create(slug='training', host=org)
        training.tags.add(Tag.objects.get(name='TTT'))
        learner = Role.objects.get(name='learner')
        Task.objects.create(person=self.trainee, event=training, role=learner)

    def test_accepted_request_are_always_valid(self):
        """Accepted training requests are valid regardless of whether they
        are matched to a training."""
        req = create_training_request(state='a', person=None)
        req.full_clean()

        req = create_training_request(state='a', person=self.admin)
        req.full_clean()

        req = create_training_request(state='a', person=self.trainee)
        req.full_clean()

    def test_valid_pending_request(self):
        req = create_training_request(state='p', person=None)
        req.full_clean()

        req = create_training_request(state='p', person=self.admin)
        req.full_clean()

    def test_pending_request_must_not_be_matched(self):
        req = create_training_request(state='p', person=self.trainee)
        with self.assertRaises(ValidationError):
            req.full_clean()


class TestTrainingRequestsListView(TestBase):
    def setUp(self):
        self._setUpAirports()
        self._setUpNonInstructors()
        self._setUpRoles()
        self._setUpTags()
        self._setUpUsersAndLogin()

        self.first_req = create_training_request(state='d',
                                                 person=self.spiderman)
        self.second_req = create_training_request(state='p', person=None)
        self.third_req = create_training_request(state='a',
                                                 person=self.ironman)
        org = Organization.objects.create(domain='example.com',
                                          fullname='Test Organization')
        self.learner = Role.objects.get(name='learner')
        self.ttt = Tag.objects.get(name='TTT')

        self.first_training = Event.objects.create(slug='ttt-event', host=org)
        self.first_training.tags.add(self.ttt)
        Task.objects.create(person=self.spiderman, role=self.learner,
                            event=self.first_training)
        self.second_training = Event.objects.create(slug='second-ttt-event',
                                                    host=org)
        self.second_training.tags.add(self.ttt)

    def test_view_loads(self):
        rv = self.client.get(reverse('all_trainingrequests'))
        self.assertEqual(rv.status_code, 200)
        # By default, only pending and accepted requests are displayed,
        # therefore, self.first_req is missing.
        self.assertEqual(set(rv.context['requests']),
                         {self.second_req, self.third_req})

    def test_successful_bulk_discard(self):
        data = {
            'discard': '',
            'requests': [self.first_req.pk, self.second_req.pk],
        }
        rv = self.client.post(reverse('all_trainingrequests'), data,
                              follow=True)

        self.assertTrue(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainingrequests')
        msg = 'Successfully discarded selected requests.'
        self.assertContains(rv, msg)
        self.first_req.refresh_from_db()
        self.assertEqual(self.first_req.state, 'd')
        self.second_req.refresh_from_db()
        self.assertEqual(self.second_req.state, 'd')
        self.third_req.refresh_from_db()
        self.assertEqual(self.third_req.state, 'a')

    def test_successful_matching_to_training(self):
        data = {
            'match': '',
            'event_1': self.second_training.pk,
            'requests': [self.first_req.pk],
        }
        rv = self.client.post(reverse('all_trainingrequests'), data,
                              follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainingrequests')
        msg = 'Successfully matched selected people to training.'
        self.assertContains(rv, msg)
        self.assertEqual(set(Event.objects.filter(task__person=self.spiderman,
                                                  task__role__name='learner')),
                         {self.first_training, self.second_training})
        self.assertEqual(set(Event.objects.filter(task__person=self.ironman,
                                                  task__role__name='learner')),
                         set())

    def test_successful_matching_twice_to_the_same_training(self):
        data = {
            'match': '',
            'event_1': self.first_training.pk,
            'requests': [self.first_req.pk],
        }
        # Spiderman is already matched with first_training
        assert self.spiderman.get_training_tasks()[0].event == self.first_training

        rv = self.client.post(reverse('all_trainingrequests'), data,
                              follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainingrequests')
        msg = 'Successfully matched selected people to training.'
        self.assertContains(rv, msg)
        self.assertEqual(set(Event.objects.filter(task__person=self.spiderman,
                                                  task__role__name='learner')),
                         {self.first_training})

    def test_matching_to_training_fails_in_the_case_of_unmatched_persons(self):
        """Requests that are not matched with any trainee account cannot be
        matched with a training. """

        data = {
            'match': '',
            'event_1': self.second_training.pk,
            'requests': [self.first_req.pk, self.second_req.pk],
        }
        # Spiderman is already matched with first_training
        assert (self.spiderman.get_training_tasks()[0].event ==
                self.first_training)

        rv = self.client.post(reverse('all_trainingrequests'), data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainingrequests')
        msg = 'Fix errors below and try again.'
        self.assertContains(rv, msg)
        msg = ('Some of the requests are not matched to a trainee yet. Before '
               'matching them to a training, you need to accept them '
               'and match with a trainee.')
        self.assertContains(rv, msg)
        # Check that Spiderman is not matched to second_training even though
        # he was selected.
        self.assertEqual(set(Event.objects.filter(task__person=self.spiderman,
                                                  task__role__name='learner')),
                         {self.first_training})

    def test_successful_unmatching(self):
        data = {
            'unmatch': '',
            'requests': [self.first_req.pk],
        }
        rv = self.client.post(reverse('all_trainingrequests'), data,
                              follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainingrequests')
        msg = 'Successfully unmatched selected people from trainings.'
        self.assertContains(rv, msg)

        self.assertEqual(set(Event.objects.filter(task__person=self.spiderman,
                                                  task__role__name='learner')),
                         set())

    def test_unmatching_fails_when_no_matched_trainee(self):
        """Requests that are not matched with any trainee cannot be
        unmatched from a training."""

        data = {
            'unmatch': '',
            'requests': [self.first_req.pk, self.second_req.pk],
        }
        rv = self.client.post(reverse('all_trainingrequests'), data,
                              follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainingrequests')
        msg = 'Fix errors below and try again.'
        self.assertContains(rv, msg)

        # Check that Spiderman is still matched to first_training even though
        # he was selected.
        self.assertEqual(set(Event.objects.filter(task__person=self.spiderman,
                                                  task__role__name='learner')),
                         {self.first_training})


class TestDownloadCSVView(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

    def test_basic(self):
        create_training_request(state='p', person=None)
        rv = self.client.get(reverse('download_trainingrequests'))
        self.assertEqual(rv.status_code, 200)
        got = rv.content.decode('utf-8')
        expected = (
            'State,Matched Trainee,Group Name,Personal,Family,Email,GitHub username,Occupation,Occupation (other),Affiliation,Location,Country,Expertise areas,Expertise areas (other),Under-represented,Previous Involvement,Previous Training in Teaching,Previous Training (other),Previous Training (explanation),Programming Language Usage,Reason,Teaching Frequency Expectation,Teaching Frequency Expectation (other),Max Travelling Frequency,Max Travelling Frequency (other),Comment\r\n'
            'Pending,—,,John,Smith,john@smith.com,,Other (enter below),,AGH University of Science and Technology,Cracow,PL,,,No,,None,,,Every day,Just for fun.,Several times a year,,Once a year,,\r\n'
        )
        self.assertEqual(got, expected)


class TestMatchingTrainingRequestAndDetailedView(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpRoles()

    def test_detailed_view_of_pending_request(self):
        """Match Request form should be displayed only when no account is
        matched. """
        req = create_training_request(state='p', person=None)
        rv = self.client.get(reverse('trainingrequest_details', args=[req.pk]))
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, 'Match Request to AMY account')

    def test_detailed_view_of_accepted_request(self):
        """Match Request form should be displayed only when no account is
        matched. """
        req = create_training_request(state='p', person=self.admin)
        rv = self.client.get(reverse('trainingrequest_details', args=[req.pk]))
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, 'Match Request to AMY account')

    def test_person_is_suggested(self):
        req = create_training_request(state='p', person=None)
        p = Person.objects.create_user(username='john_smith', personal='john',
                                       family='smith', email='asdf@gmail.com')
        rv = self.client.get(reverse('trainingrequest_details', args=[req.pk]))

        self.assertEqual(rv.context['form'].initial['person'], p)

    def test_new_person(self):
        req = create_training_request(state='p', person=None)
        rv = self.client.get(reverse('trainingrequest_details', args=[req.pk]))

        self.assertEqual(rv.context['form'].initial['person'], None)

    def test_matching_with_existing_account_works(self):
        """Regression test for [#949].

        [#949] https://github.com/swcarpentry/amy/pull/949/"""

        req = create_training_request(state='p', person=None)
        rv = self.client.post(reverse('trainingrequest_details', args=[req.pk]),
                              data={'person_1': self.admin.pk,
                                    'match-selected-person': ''},
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.state, 'p')
        self.assertEqual(req.person, self.admin)

    def test_matching_with_new_account_works(self):
        req = create_training_request(state='p', person=None)
        rv = self.client.post(reverse('trainingrequest_details', args=[req.pk]),
                              data={'create-new-person': ''},
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.state, 'p')


class TestTrainingRequestTemplateTags(TestBase):
    def test_pending_request(self):
        self._test(state='p', expected='label label-warning')

    def test_accepted_request(self):
        self._test(state='a', expected='label label-success')

    def test_discarded_request(self):
        self._test(state='d', expected='label label-danger')

    def _test(self, state, expected):
        template = Template(
            '{% load training_request %}'
            '{% training_request_label req %}'
        )
        training_request = TrainingRequest(state=state)
        context = Context({'req': training_request})
        got = template.render(context)
        self.assertEqual(got, expected)
