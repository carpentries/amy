from datetime import datetime, timezone
import unittest
from urllib.parse import urlencode

from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.template import Context
from django.template import Template
from django.urls import reverse
from django_comments.models import Comment

from extrequests.forms import TrainingRequestsMergeForm
from workshops.tests.base import TestBase
from workshops.models import (
    Person,
    Role,
    TrainingRequest,
    Organization,
    Event,
    Tag,
    Task,
    KnowledgeDomain,
)


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


class TestTrainingRequestModelScoring(TestBase):
    def setUp(self):
        self._setUpRoles()

        self.tr = TrainingRequest.objects.create(
            personal='John',
            family='Smith',
            email='john@smith.com',
            occupation='',
            affiliation='',
            location='Washington',
            country='US',
            previous_training='none',
            previous_experience='none',
            programming_language_usage_frequency='never',
            reason='Just for fun.',
            teaching_frequency_expectation='monthly',
            max_travelling_frequency='yearly',
            state='p',
        )

    def test_minimal_response_no_score(self):
        self.assertEqual(self.tr.score_auto, 0)

    def test_country(self):
        # a sample country that scores a point
        self.tr.country = 'W3'
        self.tr.save()
        self.assertEqual(self.tr.score_auto, 1)

    def test_underresourced_institution(self):
        # a sample country that scores a point
        self.tr.underresourced = True
        self.tr.save()
        self.assertEqual(self.tr.score_auto, 1)

    def test_country_and_underresourced_institution(self):
        # a sample country that scores a point
        self.tr.country = 'W3'
        self.tr.underresourced = True
        self.tr.save()
        self.assertEqual(self.tr.score_auto, 2)

    def test_domains(self):
        """Ensure m2m_changed signals work correctly on
        `TrainingRequest.domains` field."""
        # test adding a domain
        domain = KnowledgeDomain.objects.get(name='Humanities')
        self.tr.domains.add(domain)
        self.assertEqual(self.tr.score_auto, 1)

        # test removing a domain
        # domain.trainingrequest_set.remove(self.tr)
        self.tr.domains.remove(domain)
        self.assertEqual(len(self.tr.domains.all()), 0)
        self.assertEqual(self.tr.score_auto, 0)

        # test setting domains
        domains = KnowledgeDomain.objects.filter(name__in=[
            'Humanities', 'Library and information science',
            'Economics/business', 'Social sciences',
        ])
        self.tr.domains.set(domains)
        self.assertEqual(self.tr.score_auto, 1)

    def test_previous_involvement(self):
        """Ensure m2m_changed signals work correctly on
        `TrainingRequest.previous_involvement` field."""
        roles = Role.objects.all()
        self.tr.previous_involvement.add(roles[0])
        self.assertEqual(self.tr.score_auto, 1)
        self.tr.previous_involvement.add(roles[1])
        self.assertEqual(self.tr.score_auto, 2)
        self.tr.previous_involvement.add(roles[2])
        self.assertEqual(self.tr.score_auto, 3)
        self.tr.previous_involvement.add(roles[3])
        # previous involvement scoring max's out at 3
        self.assertEqual(self.tr.score_auto, 3)

    def test_previous_training_in_teaching(self):
        """Go through all options in `previous_training` and ensure only some
        produce additional score."""
        choices = TrainingRequest.PREVIOUS_TRAINING_CHOICES
        for choice, desc in choices:
            self.tr.previous_training = choice
            self.tr.save()
            if choice in ['course', 'full']:
                self.assertEqual(self.tr.score_auto, 1)
            else:
                self.assertEqual(self.tr.score_auto, 0)

    def test_previous_experience_in_teaching(self):
        """Go through all options in `previous_experience` and ensure only some
        produce additional score."""
        choices = TrainingRequest.PREVIOUS_EXPERIENCE_CHOICES
        for choice, desc in choices:
            self.tr.previous_experience = choice
            self.tr.save()
            if choice in ['ta', 'courses']:
                self.assertEqual(self.tr.score_auto, 1)
            else:
                self.assertEqual(self.tr.score_auto, 0)

    def test_tooling(self):
        """Go through all options in `programming_language_usage_frequency`
        and ensure only some produce additional score."""
        choices = TrainingRequest.PROGRAMMING_LANGUAGE_USAGE_FREQUENCY_CHOICES
        for choice, desc in choices:
            self.tr.programming_language_usage_frequency = choice
            self.tr.save()
            if choice in ['daily', 'weekly']:
                self.assertEqual(self.tr.score_auto, 1)
            else:
                self.assertEqual(self.tr.score_auto, 0)


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

    @unittest.expectedFailure
    def test_view_loads(self):
        # Regression: django-filters doesn't trigger the filter's underlying
        # method, therefore doesn't change default choice for filter to one
        # that filters out dismissed requests.
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

    def test_successful_bulk_accept(self):
        data = {
            'accept': '',
            'requests': [self.first_req.pk, self.second_req.pk],
        }
        rv = self.client.post(reverse('all_trainingrequests'), data,
                              follow=True)

        self.assertTrue(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainingrequests')
        msg = 'Successfully accepted selected requests.'
        self.assertContains(rv, msg)
        self.first_req.refresh_from_db()
        self.assertEqual(self.first_req.state, 'a')
        self.second_req.refresh_from_db()
        self.assertEqual(self.second_req.state, 'a')
        self.third_req.refresh_from_db()
        self.assertEqual(self.third_req.state, 'a')

    def test_successful_matching_to_training(self):
        data = {
            'match': '',
            'event': self.second_training.pk,
            'requests': [self.first_req.pk],
        }
        rv = self.client.post(reverse('all_trainingrequests'), data,
                              follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainingrequests')
        msg = 'Successfully accepted and matched selected people to training.'
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
            'event': self.first_training.pk,
            'requests': [self.first_req.pk],
        }
        # Spiderman is already matched with first_training
        assert self.spiderman.get_training_tasks()[0].event == self.first_training

        rv = self.client.post(reverse('all_trainingrequests'), data,
                              follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainingrequests')
        msg = 'Successfully accepted and matched selected people to training.'
        self.assertContains(rv, msg)
        self.assertEqual(set(Event.objects.filter(task__person=self.spiderman,
                                                  task__role__name='learner')),
                         {self.first_training})

    def test_trainee_accepted_during_matching(self):
        # this request is set up without matched person
        self.second_req.person = self.spiderman
        self.second_req.save()
        self.assertEqual(self.second_req.state, 'p')

        data = {
            'match': '',
            'event': self.second_training.pk,
            'requests': [self.second_req.pk],
        }
        rv = self.client.post(reverse('all_trainingrequests'), data,
                              follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainingrequests')
        msg = 'Successfully accepted and matched selected people to training.'
        self.assertContains(rv, msg)
        self.second_req.refresh_from_db()
        self.assertEqual(self.second_req.state, 'a')

    def test_matching_to_training_fails_in_the_case_of_unmatched_persons(self):
        """Requests that are not matched with any trainee account cannot be
        matched with a training. """

        data = {
            'match': '',
            'event': self.second_training.pk,
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


class TestMatchingTrainingRequestAndDetailedView(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpRoles()
        self._setUpAirports()
        self._setUpNonInstructors()

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
        rv = self.client.post(reverse('trainingrequest_details',
                                      args=[req.pk]),
                              data={'person': self.ironman.pk,
                                    'match-selected-person': ''},
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.state, 'p')
        self.assertEqual(req.person, self.ironman)

        self.ironman.refresh_from_db()

        # in response to #1270, check if person record was updated
        data_expected = {
            'personal': req.personal,
            'middle': req.middle,
            'family': req.family,
            'email': req.email,
            'country': req.country,
            'github': req.github or None,
            'affiliation': req.affiliation,
            'occupation': req.get_occupation_display() if req.occupation
                else req.occupation_other,
            'data_privacy_agreement': req.data_privacy_agreement,
            'may_contact': True,
            'is_active': True,
        }
        for key, value in data_expected.items():
            self.assertEqual(getattr(self.ironman, key), value,
                             'Attribute: {}'.format(key))
        self.assertEqual(set(self.ironman.domains.all()),
                         set(req.domains.all()))

    def test_matching_with_new_account_works(self):
        req = create_training_request(state='p', person=None)
        rv = self.client.post(reverse('trainingrequest_details', args=[req.pk]),
                              data={'create-new-person': ''},
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.state, 'p')

        # in response to #1270, check if person record was updated
        data_expected = {
            'personal': req.personal,
            'middle': req.middle,
            'family': req.family,
            'email': req.email,
            'country': req.country,
            'github': req.github or None,
            'affiliation': req.affiliation,
            'occupation': req.get_occupation_display() if req.occupation
                else req.occupation_other,
            'data_privacy_agreement': req.data_privacy_agreement,
            'may_contact': True,
            'is_active': True,
        }
        for key, value in data_expected.items():
            self.assertEqual(getattr(req.person, key), value,
                             'Attribute: {}'.format(key))
        self.assertEqual(set(req.person.domains.all()), set(req.domains.all()))


class TestTrainingRequestTemplateTags(TestBase):
    def test_pending_request(self):
        self._test(state='p', expected='badge badge-warning')

    def test_accepted_request(self):
        self._test(state='a', expected='badge badge-success')

    def test_discarded_request(self):
        self._test(state='d', expected='badge badge-danger')

    def _test(self, state, expected):
        template = Template(
            '{% load state %}'
            '{% state_label req %}'
        )
        training_request = TrainingRequest(state=state)
        context = Context({'req': training_request})
        got = template.render(context)
        self.assertEqual(got, expected)


class TestTrainingRequestMerging(TestBase):
    # there's little need to check for extra corner cases
    # because they're covered by merging tests in `test_person`
    # and `test_event`

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

        # comments regarding first request
        self.ca = Comment.objects.create(
            content_object=self.first_req,
            user=self.spiderman,
            comment="Comment from admin on first_req",
            submit_date=datetime.now(tz=timezone.utc),
            site=Site.objects.get_current(),
        )
        # comments regarding second request
        self.cb = Comment.objects.create(
            content_object=self.second_req,
            user=self.ironman,
            comment="Comment from admin on second_req",
            submit_date=datetime.now(tz=timezone.utc),
            site=Site.objects.get_current(),
        )

        # assign roles (previous involvement with The Carpentries) and
        # knowledge domains - those are the hardest to merge successfully
        self.chemistry = KnowledgeDomain.objects.get(name='Chemistry')
        self.physics = KnowledgeDomain.objects.get(name='Physics')
        self.humanities = KnowledgeDomain.objects.get(name='Humanities')
        self.education = KnowledgeDomain.objects.get(name='Education')
        self.social = KnowledgeDomain.objects.get(name='Social sciences')
        self.first_req.domains.set([self.chemistry, self.physics])
        self.second_req.domains.set([self.humanities, self.social])
        self.third_req.domains.set([self.education])

        self.learner = Role.objects.get(name='learner')
        self.helper = Role.objects.get(name='helper')
        self.instructor = Role.objects.get(name='instructor')
        self.contributor = Role.objects.get(name='contributor')
        self.first_req.previous_involvement.set([self.learner])
        self.second_req.previous_involvement.set([self.helper])
        self.third_req.previous_involvement.set([self.instructor,
                                                 self.contributor])

        # prepare merge strategies (POST data to be sent to the merging view)
        self.strategy_1 = {
            'trainingrequest_a': self.first_req.pk,
            'trainingrequest_b': self.second_req.pk,
            'id': 'obj_a',
            'state': 'obj_b',
            'person': 'obj_a',
            'group_name': 'obj_a',
            'personal': 'obj_a',
            'middle': 'obj_a',
            'family': 'obj_a',
            'email': 'obj_a',
            'github': 'obj_a',
            'occupation': 'obj_a',
            'occupation_other': 'obj_a',
            'affiliation': 'obj_a',
            'location': 'obj_a',
            'country': 'obj_a',
            'underresourced': 'obj_a',
            'domains': 'obj_a',
            'domains_other': 'obj_a',
            'underrepresented': 'obj_a',
            'nonprofit_teaching_experience': 'obj_a',
            'previous_involvement': 'obj_b',
            'previous_training': 'obj_a',
            'previous_training_other': 'obj_a',
            'previous_training_explanation': 'obj_a',
            'previous_experience': 'obj_a',
            'previous_experience_other': 'obj_a',
            'previous_experience_explanation': 'obj_a',
            'programming_language_usage_frequency': 'obj_a',
            'teaching_frequency_expectation': 'obj_a',
            'teaching_frequency_expectation_other': 'obj_a',
            'max_travelling_frequency': 'obj_a',
            'max_travelling_frequency_other': 'obj_a',
            'reason': 'obj_a',
            'comment': 'obj_a',
            'training_completion_agreement': 'obj_a',
            'workshop_teaching_agreement': 'obj_a',
            'data_privacy_agreement': 'obj_a',
            'code_of_conduct_agreement': 'obj_a',
            'created_at': 'obj_a',
            'comments': 'combine',
        }
        self.strategy_2 = {
            'trainingrequest_a': self.first_req.pk,
            'trainingrequest_b': self.third_req.pk,
            'id': 'obj_b',
            'state': 'obj_a',
            'person': 'obj_a',
            'group_name': 'obj_b',
            'personal': 'obj_b',
            'middle': 'obj_b',
            'family': 'obj_b',
            'email': 'obj_b',
            'github': 'obj_b',
            'occupation': 'obj_b',
            'occupation_other': 'obj_b',
            'affiliation': 'obj_b',
            'location': 'obj_b',
            'country': 'obj_b',
            'underresourced': 'obj_b',
            'domains': 'combine',
            'domains_other': 'obj_b',
            'underrepresented': 'obj_b',
            'nonprofit_teaching_experience': 'obj_b',
            'previous_involvement': 'combine',
            'previous_training': 'obj_a',
            'previous_training_other': 'obj_a',
            'previous_training_explanation': 'obj_a',
            'previous_experience': 'obj_a',
            'previous_experience_other': 'obj_a',
            'previous_experience_explanation': 'obj_a',
            'programming_language_usage_frequency': 'obj_a',
            'teaching_frequency_expectation': 'obj_a',
            'teaching_frequency_expectation_other': 'obj_a',
            'max_travelling_frequency': 'obj_a',
            'max_travelling_frequency_other': 'obj_a',
            'reason': 'obj_a',
            'comment': 'obj_a',
            'training_completion_agreement': 'obj_a',
            'workshop_teaching_agreement': 'obj_a',
            'data_privacy_agreement': 'obj_a',
            'code_of_conduct_agreement': 'obj_a',
            'created_at': 'obj_a',
            'comments': 'combine',
        }

        base_url = reverse('trainingrequests_merge')
        query_1 = urlencode({
            'trainingrequest_a': self.first_req.pk,
            'trainingrequest_b': self.second_req.pk,
        })
        query_2 = urlencode({
            'trainingrequest_a': self.first_req.pk,
            'trainingrequest_b': self.third_req.pk,
        })
        self.url_1 = '{}?{}'.format(base_url, query_1)
        self.url_2 = '{}?{}'.format(base_url, query_2)

    def test_form_invalid_values(self):
        """Make sure only a few fields accept third option ("combine")."""
        hidden = {
            'trainingrequest_a': self.first_req.pk,
            'trainingrequest_b': self.second_req.pk,
        }
        # fields accepting only 2 options: "obj_a" and "obj_b"
        failing = {
            'id': 'combine',
            'state': 'combine',
            'person': 'combine',
            'group_name': 'combine',
            'personal': 'combine',
            'middle': 'combine',
            'family': 'combine',
            'email': 'combine',
            'github': 'combine',
            'occupation': 'combine',
            'occupation_other': 'combine',
            'affiliation': 'combine',
            'location': 'combine',
            'country': 'combine',
            'underresourced': 'combine',
            'domains_other': 'combine',
            'underrepresented': 'combine',
            'nonprofit_teaching_experience': 'combine',
            'previous_training': 'combine',
            'previous_training_other': 'combine',
            'previous_training_explanation': 'combine',
            'previous_experience': 'combine',
            'previous_experience_other': 'combine',
            'previous_experience_explanation': 'combine',
            'programming_language_usage_frequency': 'combine',
            'teaching_frequency_expectation': 'combine',
            'teaching_frequency_expectation_other': 'combine',
            'max_travelling_frequency': 'combine',
            'max_travelling_frequency_other': 'combine',
            'training_completion_agreement': 'combine',
            'workshop_teaching_agreement': 'combine',
            'data_privacy_agreement': 'combine',
            'code_of_conduct_agreement': 'combine',
            'created_at': 'combine',
        }
        # fields additionally accepting "combine"
        passing = {
            'domains': 'combine',
            'previous_involvement': 'combine',
            'reason': 'combine',
            'comment': 'combine',
            'comments': 'combine',
        }
        data = hidden.copy()
        data.update(failing)
        data.update(passing)

        form = TrainingRequestsMergeForm(data)
        self.assertFalse(form.is_valid())

        for key in failing:
            self.assertIn(key, form.errors)
        for key in passing:
            self.assertNotIn(key, form.errors)

        # make sure no fields are added without this test being updated
        self.assertEqual(set(list(form.fields.keys())), set(list(data.keys())))

    def test_merging_base_trainingrequest(self):
        """Merging: ensure the base training request is selected based on ID
        form field.

        If ID field has a value of 'obj_b', then 1st training req is base and
        it won't be removed from the database after the merge. 2nd training
        req, on the other hand, will."""
        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)

        self.first_req.refresh_from_db()
        with self.assertRaises(TrainingRequest.DoesNotExist):
            self.second_req.refresh_from_db()

    def test_merging_basic_attributes(self):
        """Merging: ensure basic (non-relationships) attributes are properly
        saved."""
        assertions = {
            'id': self.first_req.id,
            'state': self.second_req.state,
            'person': self.first_req.person,
            'group_name': self.first_req.group_name,
            'personal': self.first_req.personal,
            'middle': self.first_req.middle,
            'family': self.first_req.family,
            'email': self.first_req.email,
            'github': self.first_req.github,
            'occupation': self.first_req.occupation,
            'occupation_other': self.first_req.occupation_other,
            'affiliation': self.first_req.affiliation,
            'location': self.first_req.location,
            'country': self.first_req.country,
            'underresourced': self.first_req.underresourced,
            'domains_other': self.first_req.domains_other,
            'underrepresented': self.first_req.underrepresented,
            'nonprofit_teaching_experience':
                self.first_req.nonprofit_teaching_experience,
            'previous_training': self.first_req.previous_training,
            'previous_training_other': self.first_req.previous_training_other,
            'previous_training_explanation':
                self.first_req.previous_training_explanation,
            'previous_experience': self.first_req.previous_experience,
            'previous_experience_other':
                self.first_req.previous_experience_other,
            'previous_experience_explanation':
                self.first_req.previous_experience_explanation,
            'programming_language_usage_frequency':
                self.first_req.programming_language_usage_frequency,
            'teaching_frequency_expectation':
                self.first_req.teaching_frequency_expectation,
            'teaching_frequency_expectation_other':
                self.first_req.teaching_frequency_expectation_other,
            'max_travelling_frequency':
                self.first_req.max_travelling_frequency,
            'max_travelling_frequency_other':
                self.first_req.max_travelling_frequency_other,
            'reason': self.first_req.reason,
            'comment': self.first_req.comment,
            'training_completion_agreement':
                self.first_req.training_completion_agreement,
            'workshop_teaching_agreement':
                self.first_req.workshop_teaching_agreement,
            'data_privacy_agreement': self.first_req.data_privacy_agreement,
            'code_of_conduct_agreement':
                self.first_req.code_of_conduct_agreement,
            'created_at': self.first_req.created_at,
        }
        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)
        self.first_req.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(getattr(self.first_req, key), value, key)

    def test_merging_relational_attributes(self):
        """Merging: ensure relational fields are properly saved/combined."""
        assertions = {
            'domains': set([self.chemistry, self.physics]),
            'previous_involvement': set([self.helper]),
            # comments are not relational, they're related via generic FKs,
            # so they won't appear here
        }

        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)
        self.first_req.refresh_from_db()

        for key, value in assertions.items():
            self.assertEqual(
                set(getattr(self.first_req, key).all()),
                value,
                key)

    def test_merging(self):
        rv = self.client.post(self.url_1, self.strategy_1, follow=True)
        self.assertTrue(rv.status_code, 200)
        # after successful merge, we should end up redirected to the details
        # page of the base object
        self.assertEqual(rv.resolver_match.view_name,
                         'trainingrequest_details')

        # check if objects merged
        self.first_req.refresh_from_db()
        with self.assertRaises(TrainingRequest.DoesNotExist):
            self.second_req.refresh_from_db()
        self.third_req.refresh_from_db()

        # try second strategy
        rv = self.client.post(self.url_2, self.strategy_2, follow=True)
        self.assertTrue(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name,
                         'trainingrequest_details')

        # check if objects merged
        with self.assertRaises(TrainingRequest.DoesNotExist):
            self.first_req.refresh_from_db()
        with self.assertRaises(TrainingRequest.DoesNotExist):
            self.second_req.refresh_from_db()
        self.third_req.refresh_from_db()

        # check if third request properties changed accordingly
        self.assertEqual(self.third_req.personal, 'John')
        self.assertEqual(self.third_req.family, 'Smith')
        self.assertEqual(self.third_req.state, 'p')
        self.assertEqual(self.third_req.person, self.spiderman)
        domains_set = set([self.chemistry, self.physics, self.education])
        roles_set = set([self.helper, self.instructor, self.contributor])
        self.assertEqual(domains_set,
                         set(self.third_req.domains.all()))
        self.assertEqual(roles_set,
                         set(self.third_req.previous_involvement.all()))

        # make sure no M2M related objects were removed from DB
        self.chemistry.refresh_from_db()
        self.physics.refresh_from_db()
        self.humanities.refresh_from_db()
        self.education.refresh_from_db()
        self.social.refresh_from_db()

        self.learner.refresh_from_db()
        self.helper.refresh_from_db()
        self.instructor.refresh_from_db()
        self.contributor.refresh_from_db()

        # make sure no related persons were removed from DB
        self.ironman.refresh_from_db()
        self.spiderman.refresh_from_db()

    def test_merging_comments_strategy1(self):
        """Ensure comments regarding persons are correctly merged using
        `merge_objects`.
        This test uses strategy 1 (combine)."""
        self.strategy_1['comments'] = 'combine'
        comments = [self.ca, self.cb]
        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)
        self.first_req.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.first_req)
                               .filter(is_removed=False)),
            set(comments),
        )

    def test_merging_comments_strategy2(self):
        """Ensure comments regarding persons are correctly merged using
        `merge_objects`.
        This test uses strategy 2 (object a)."""
        self.strategy_1['comments'] = 'obj_a'
        comments = [self.ca]
        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)
        self.first_req.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.first_req)
                               .filter(is_removed=False)),
            set(comments),
        )

    def test_merging_comments_strategy3(self):
        """Ensure comments regarding persons are correctly merged using
        `merge_objects`.
        This test uses strategy 3 (object b)."""
        self.strategy_1['comments'] = 'obj_b'
        comments = [self.cb]
        rv = self.client.post(self.url_1, data=self.strategy_1)
        self.assertEqual(rv.status_code, 302)
        self.first_req.refresh_from_db()
        self.assertEqual(
            set(Comment.objects.for_model(self.first_req)
                               .filter(is_removed=False)),
            set(comments),
        )
