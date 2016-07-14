import datetime

from django.core.urlresolvers import reverse

from ..models import Event, Task, Role
from .base import TestBase


class TestInstructorsByDate(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

        self.today = datetime.date.today()
        self.tomorrow = self.today + datetime.timedelta(days=1)
        self.yesterday = self.today - datetime.timedelta(days=1)
        self.after_tomorrow = self.today + datetime.timedelta(days=2)

        # set up some testing Events
        self.e1 = Event.objects.create(
            host=self.org_alpha,
            slug="in-range",
            start=self.today,
            end=self.tomorrow,
        )

        self.e2 = Event.objects.create(
            host=self.org_alpha,
            slug="out-of-range1",
            start=self.yesterday,
            end=self.tomorrow,
        )

        self.e3 = Event.objects.create(
            host=self.org_alpha,
            slug="out-of-range2",
            start=self.today,
            end=self.after_tomorrow,
        )

        self.role = Role.objects.create(name='instructor')
        Task.objects.create(event=self.e1, person=self.hermione,
                            role=self.role)
        Task.objects.create(event=self.e2, person=self.hermione,
                            role=self.role)
        Task.objects.create(event=self.e3, person=self.hermione,
                            role=self.role)

    def test_debrief(self):
        "Make sure proper events are returned withing specific date ranges."
        data = {
            'begin_date': self.today,
            'end_date': self.tomorrow,
            'url': reverse('instructors_by_date'),
        }
        FMT = '{url}?begin_date={begin_date}&end_date={end_date}'

        rv = self.client.get(FMT.format_map(data))
        assert rv.status_code == 200
        content = rv.content.decode('utf-8')
        assert self.e1.slug in content
        assert self.e2.slug not in content
        assert self.e3.slug not in content

        data['begin_date'] = self.yesterday
        rv = self.client.get(FMT.format_map(data))
        assert rv.status_code == 200
        content = rv.content.decode('utf-8')
        assert self.e1.slug in content
        assert self.e2.slug in content
        assert self.e3.slug not in content

        data['end_date'] = self.after_tomorrow
        rv = self.client.get(FMT.format_map(data))
        assert rv.status_code == 200
        content = rv.content.decode('utf-8')
        assert self.e1.slug in content
        assert self.e2.slug in content
        assert self.e3.slug in content

        data['begin_date'] = self.today
        rv = self.client.get(FMT.format_map(data))
        assert rv.status_code == 200
        content = rv.content.decode('utf-8')
        assert self.e1.slug in content
        assert self.e2.slug not in content
        assert self.e3.slug in content
