from django.core.urlresolvers import reverse

from .base import TestBase
from ..models import Badge, Award, Person, Event


class TestBadge(TestBase):
    """Tests for badge model and views, including some tests for awards."""

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_badge_display(self):
        """Ensure the badge is displayed correctly on its details page."""
        rv = self.client.get(reverse('badge_details',
                                     args=(self.instructor.name, )))
        content = rv.content.decode('utf-8')
        assert self.instructor.name in content
        assert self.instructor.title in content
        assert self.instructor.criteria in content
        self._check_status_code_and_parse(rv, 200)

    def test_badge_display_awards(self):
        "Ensure awards are displayed correctly on their badge details page."
        rv = self.client.get(reverse('badge_details',
                                     args=(self.instructor.name, )))
        content = rv.content.decode('utf-8')

        awards = self.instructor.award_set.all()
        for award in awards:
            assert award.person.get_full_name() in content, \
                "Award for {} not found".format(award.person)

    def test_badge_award(self):
        """Ensure we can add awards from badge details page."""
        url, values = self._get_initial_form('badge_details',
                                             self.instructor.name)
        print(values)
        print(url)
        values['person_1'] = self.spiderman.id

        # to override django-selectable behavior
        values['person_0'] = ''
        values['event_1'] = ''
        values['event_0'] = ''

        assert self.instructor.award_set.count() == 3

        response = self.client.post(url, values)
        self._check_status_code_and_parse(response, 200)

        assert self.instructor.award_set.count() == 4
