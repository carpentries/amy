from datetime import datetime

from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.urls import reverse

from workshops.forms import TrainingProgressForm
from workshops.models import (
    TrainingProgress,
    TrainingRequirement,
    Event,
    Tag,
    Organization,
    Role,
)
from workshops.tests import TestBase


class TestTrainingProgressValidation(TestBase):
    """Test that validation errors appear near right fields (url and event)."""

    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpAirports()
        self._setUpNonInstructors()

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

    def test_form_invalid_if_trainee_has_no_training_task(self):
        data = {
            'requirement': self.requirement.pk,
            'state': 'p',
            'evaluated_by': self.admin.pk,
            'trainee': self.ironman.pk,
        }
        form = TrainingProgressForm(data)
        self.assertEqual(form.is_valid(), False)
        self.assertIn("not possible to add training progress",
                      form.non_field_errors()[0])


class TestProgressLabelTemplateTag(TestBase):
    def test_passed(self):
        self._test(state='p', discarded=False, expected='badge badge-success')

    def test_not_evaluated_yet(self):
        self._test(state='n', discarded=False, expected='badge badge-warning')

    def test_failed(self):
        self._test(state='f', discarded=False, expected='badge badge-danger')

    def test_discarded(self):
        self._test(state='p', discarded=True, expected='badge badge-dark')
        self._test(state='n', discarded=True, expected='badge badge-dark')
        self._test(state='f', discarded=True, expected='badge badge-dark')

    def _test(self, state, discarded, expected):
        template = Template(
            r'{% load training_progress %}'
            r'{% progress_label p %}'
        )
        training_progress = TrainingProgress(state=state, discarded=discarded)
        context = Context({'p': training_progress})
        got = template.render(context)
        self.assertEqual(got, expected)


class TestProgressDescriptionTemplateTag(TestBase):
    def setUp(self):
        self._setUpAirports()
        self._setUpNonInstructors()

    def test_basic(self):
        self._test(
            progress=TrainingProgress(
                state='p',
                evaluated_by=self.spiderman,
                trainee=self.ironman,
                created_at=datetime(2016, 5, 1, 16, 00),
                requirement=TrainingRequirement(name='Discussion')
            ),
            expected='Passed Discussion<br />'
                     'evaluated by Peter Q. Parker<br />'
                     'on Sunday 01 May 2016 at 16:00.',
        )

    def test_notes(self):
        self._test(
            progress=TrainingProgress(
                state='p',
                evaluated_by=self.spiderman,
                trainee=self.ironman,
                created_at=datetime(2016, 5, 1, 16, 00),
                requirement=TrainingRequirement(name='Discussion'),
                notes='Additional notes',
            ),
            expected='Passed Discussion<br />'
                     'evaluated by Peter Q. Parker<br />'
                     'on Sunday 01 May 2016 at 16:00.<br />'
                     'Notes: Additional notes',
        )

    def test_discarded(self):
        self._test(
            progress=TrainingProgress(
                state='p',
                discarded=True,
                evaluated_by=self.spiderman,
                trainee=self.ironman,
                created_at=datetime(2016, 5, 1, 16, 00),
                requirement=TrainingRequirement(name='Discussion'),
            ),
            expected='Discarded Passed Discussion<br />'
                     'evaluated by Peter Q. Parker<br />'
                     'on Sunday 01 May 2016 at 16:00.',
        )

    def test_no_mentor_or_examiner_assigned(self):
        self._test(
            progress=TrainingProgress(
                state='p',
                evaluated_by=None,
                trainee=self.ironman,
                created_at=datetime(2016, 5, 1, 16, 00),
                requirement=TrainingRequirement(name='Discussion'),
            ),
            expected='Passed Discussion<br />'
                     'submitted<br />'
                     'on Sunday 01 May 2016 at 16:00.',
        )

    def _test(self, progress, expected):
        template = Template(
            '{% load training_progress %}'
            '{% progress_description p %}'
        )
        context = Context({'p': progress})
        got = template.render(context)
        self.assertEqual(got, expected)


class TestCRUDViews(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpAirports()
        self._setUpNonInstructors()
        self._setUpTags()
        self._setUpRoles()

        self.requirement = TrainingRequirement.objects.create(name='Discussion')
        self.progress = TrainingProgress.objects.create(
            requirement=self.requirement,
            state='p',
            evaluated_by=self.admin,
            trainee=self.ironman,
        )
        self.ttt_event = Event.objects.create(
            start=datetime(2018, 7, 14),
            slug='2018-07-14-training',
            host=Organization.objects.first(),
        )
        self.ttt_event.tags.add(Tag.objects.get(name='TTT'))

    def test_create_view_loads(self):
        rv = self.client.get(reverse('trainingprogress_add'))
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.context['form'].initial['evaluated_by'], self.admin)

    def test_create_view_works_with_initial_trainee(self):
        rv = self.client.get(reverse('trainingprogress_add'), {
            'trainee': self.ironman.pk
        })
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.context['form'].initial['evaluated_by'], self.admin)
        self.assertEqual(int(rv.context['form'].initial['trainee']), self.ironman.pk)

    def test_create_view_works(self):
        data = {
            'requirement': self.requirement.pk,
            'state': 'p',
            'evaluated_by': self.admin.pk,
            'trainee': self.ironman.pk,
        }

        # in order to add training progress, the trainee needs to have
        # a training task
        self.ironman.task_set.create(
            event=self.ttt_event,
            role=Role.objects.get(name='learner'),
        )

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

    def test_delete_trainingprogress_from_edit_view(self):
        """Regression test for issue #1085."""
        trainingprogress_edit = self.app.get(
            reverse('trainingprogress_edit', args=[self.progress.pk]),
            user='admin'
        )
        self.assertRedirects(
            trainingprogress_edit.forms['delete-form'].submit(),
            reverse('all_trainees')
        )
        with self.assertRaises(TrainingProgress.DoesNotExist):
            self.progress.refresh_from_db()
