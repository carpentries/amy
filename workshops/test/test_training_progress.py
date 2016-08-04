from datetime import datetime
from django.core.urlresolvers import reverse

from django.template import Context

from django.template import Template

from django.core.exceptions import ValidationError

from workshops.models import TrainingProgress, TrainingRequirement, Event, Tag, \
    Organization
from workshops.test import TestBase


class TestTrainingProgressValidation(TestBase):
    """Test that validation errors appear near right fields (url and event)."""

    def setUp(self):
        self._setUpUsersAndLogin()

        self.requirement = TrainingRequirement.objects.create(
            name='Discussion', url_required=False, event_required=False)
        self.url_required = TrainingRequirement.objects.create(
            name='SWC Homework', url_required=True, event_required=False)
        self.event_required = TrainingRequirement.objects.create(
            name='Training', url_required=False, event_required=True)

    def test_url_is_required(self):
        p1 = TrainingProgress.objects.create(requirement=self.requirement,
                                             trainee=self.admin,
                                             evaluated_by=self.admin)
        p2 = TrainingProgress.objects.create(requirement=self.url_required,
                                             trainee=self.admin,
                                             evaluated_by=self.admin)
        p1.full_clean()
        with self.assertRaises(ValidationError):
            p2.full_clean()

    def test_url_must_be_blank(self):
        p1 = TrainingProgress.objects.create(requirement=self.requirement,
                                             trainee=self.admin,
                                             evaluated_by=self.admin,
                                             url='http://example.com')
        p2 = TrainingProgress.objects.create(requirement=self.url_required,
                                             trainee=self.admin,
                                             evaluated_by=self.admin,
                                             url='http://example.com')
        with self.assertRaises(ValidationError):
            p1.full_clean()
        p2.full_clean()

    def test_event_is_required(self):
        p1 = TrainingProgress.objects.create(requirement=self.requirement,
                                             trainee=self.admin,
                                             evaluated_by=self.admin)
        p2 = TrainingProgress.objects.create(requirement=self.event_required,
                                             trainee=self.admin,
                                             evaluated_by=self.admin)
        p1.full_clean()
        with self.assertRaises(ValidationError):
            p2.full_clean()

    def test_event_must_be_blank(self):
        org = Organization.objects.create(domain='example.com',
                                          fullname='Test Organization')
        ttt, _ = Tag.objects.get_or_create(name='TTT')
        event = Event.objects.create(slug='ttt', host=org)
        event.tags.add(ttt)
        p1 = TrainingProgress.objects.create(requirement=self.requirement,
                                             trainee=self.admin,
                                             evaluated_by=self.admin,
                                             event=event)
        p2 = TrainingProgress.objects.create(requirement=self.event_required,
                                             trainee=self.admin,
                                             evaluated_by=self.admin,
                                             event=event)
        with self.assertRaises(ValidationError):
            p1.full_clean()
        p2.full_clean()

    def test_evaluated_progress_may_have_mentor_or_examiner_associated(self):
        p1 = TrainingProgress.objects.create(requirement=self.requirement,
                                             trainee=self.admin, state='p',
                                             evaluated_by=self.admin)
        p2 = TrainingProgress.objects.create(requirement=self.requirement,
                                             trainee=self.admin, state='p',
                                             evaluated_by=None)
        p1.full_clean()
        p2.full_clean()

    def test_unevaluated_progress_may_have_mentor_or_examiner_associated(self):
        p1 = TrainingProgress.objects.create(requirement=self.requirement,
                                             trainee=self.admin, state='n',
                                             evaluated_by=self.admin)
        p2 = TrainingProgress.objects.create(requirement=self.requirement,
                                             trainee=self.admin, state='n',
                                             evaluated_by=None)
        p1.full_clean()
        p2.full_clean()


class TestCRUDViews(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpAirports()
        self._setUpNonInstructors()

        self.requirement = TrainingRequirement.objects.create(name='Discussion')
        self.progress = TrainingProgress.objects.create(
            requirement=self.requirement,
            state='p',
            evaluated_by=self.admin,
            trainee=self.ironman,
        )

    def test_create_view_loads(self):
        rv = self.client.get(reverse('trainingprogress_add'))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.context['form'].initial['evaluated_by'], self.admin)

    def test_create_view_works_with_initial_trainee(self):
        rv = self.client.get(reverse('trainingprogress_add',
                                     args=[self.ironman.pk]))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.context['form'].initial['evaluated_by'], self.admin)
        self.assertEqual(rv.context['form'].initial['trainee'], self.ironman)

    def test_create_view_works(self):
        data = {
            'requirement': self.requirement.pk,
            'state': 'p',
            'evaluated_by': self.admin.pk,
            'trainee': self.ironman.pk,
        }
        rv = self.client.post(reverse('trainingprogress_add'), data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'trainingprogress_edit')
        self.assertEqual(len(TrainingProgress.objects.all()), 2)

    def test_edit_view_loads(self):
        rv = self.client.get(reverse('trainingprogress_edit',
                                     args=[self.progress.pk]))
        self.assertEqual(rv.status_code, 200)

    def test_delete_view_get_request_not_allowed(self):
        rv = self.client.get(reverse('trainingprogress_delete',
                                     args=[self.progress.pk]))
        self.assertEqual(rv.status_code, 405)

    def test_delete_view_works(self):
        rv = self.client.post(reverse('trainingprogress_delete',
                                      args=[self.progress.pk]),
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainees')
        self.assertEqual(set(TrainingProgress.objects.all()), set())
