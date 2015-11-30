from django.core.urlresolvers import reverse

from .base import TestBase
from ..models import Tag, Event, Task, Role


class TestInstructorIssues(TestBase):
    """Tests for the `instructor_issues` view."""

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

        TTT, _ = Tag.objects.get_or_create(name='TTT')
        stalled = Tag.objects.get(name='stalled')
        learner, _ = Role.objects.get_or_create(name='learner')

        # add two TTT events, one stalled and one normal
        e1 = Event.objects.create(slug='ttt-stalled', host=self.host_alpha)
        e1.tags = [TTT, stalled]

        e2 = Event.objects.create(slug='ttt-not-stalled', host=self.host_alpha)
        e2.tags.add(TTT)

        Task.objects.create(event=e1, person=self.spiderman, role=learner)
        Task.objects.create(event=e1, person=self.ironman, role=learner)
        Task.objects.create(event=e1, person=self.blackwidow, role=learner)
        Task.objects.create(event=e2, person=self.spiderman, role=learner)

    def test_stalled_trainees_not_in_pending(self):
        """"""
        rv = self.client.get(reverse('instructor_issues'))
        pending = [t.person for t in rv.context['pending']]
        stalled = [t.person for t in rv.context['stalled']]

        self.assertIn(self.spiderman, pending)
        self.assertNotIn(self.spiderman, stalled)
        self.assertNotIn(self.ironman, pending)
        self.assertIn(self.ironman, stalled)
        self.assertNotIn(self.blackwidow, pending)
        self.assertIn(self.blackwidow, stalled)
