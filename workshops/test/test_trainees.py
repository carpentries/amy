from django.core.urlresolvers import reverse

from workshops.models import TrainingProgress, TrainingRequirement
from workshops.test.base import TestBase


class TestTraineesView(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self._setUpAirports()
        self._setUpBadges()
        self._setUpNonInstructors()

        self.training = TrainingRequirement.objects.get(name='Training')
        self.homework = TrainingRequirement.objects.get(name='SWC Homework')
        self.discussion = TrainingRequirement.objects.get(name='Discussion')

    def test_view_loads(self):
        rv = self.client.get(reverse('all_trainees'))
        self.assertEqual(rv.status_code, 200)

    def test_bulk_add_progress(self):
        TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.discussion, state='n')
        data = {
            'trainees': [self.spiderman.pk, self.ironman.pk],
            'requirement': self.discussion.pk,
            'state': 'f',
            'submit': '',
        }
        rv = self.client.post(reverse('all_trainees'), data, follow=True)

        self.assertEqual(rv.resolver_match.view_name, 'all_trainees')
        msg = 'Successfully changed progress of all selected trainees.'
        self.assertContains(rv, msg)
        got = set(TrainingProgress.objects.values_list(
            'trainee', 'requirement', 'state', 'evaluated_by'))
        expected = {
            (self.spiderman.pk, self.discussion.pk, 'n', None),
            (self.spiderman.pk, self.discussion.pk, 'f', self.admin.pk),
            (self.ironman.pk, self.discussion.pk, 'f', self.admin.pk),
        }
        self.assertEqual(got, expected)

    def test_bulk_discard_progress(self):
        spiderman_progress = TrainingProgress.objects.create(
            trainee=self.spiderman, requirement=self.discussion, state='n')
        ironman_progress = TrainingProgress.objects.create(
            trainee=self.ironman, requirement=self.discussion, state='n')
        blackwidow_progress = TrainingProgress.objects.create(
            trainee=self.blackwidow, requirement=self.discussion, state='n')
        data = {
            'trainees': [self.spiderman.pk, self.ironman.pk],
            'discard': '',
        }
        rv = self.client.post(reverse('all_trainees'), data, follow=True)

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, 'all_trainees')
        msg = 'Successfully discarded progress of all selected trainees.'
        self.assertContains(rv, msg)
        spiderman_progress.refresh_from_db()
        self.assertTrue(spiderman_progress.discarded)
        ironman_progress.refresh_from_db()
        self.assertTrue(ironman_progress.discarded)
        blackwidow_progress.refresh_from_db()
        self.assertFalse(blackwidow_progress.discarded)
