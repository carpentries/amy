from django.core.urlresolvers import reverse
from .base import TestBase


class TestLocateInstructors(TestBase):
    '''Test cases for locating instructors.'''

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_search_for_one_instructor_by_airport(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_0_0.id,
                                     'wanted' : 1})
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" not in content
        assert "Ron Weasley" not in content

    def test_search_for_two_instructors_by_airport(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_0_0.id,
                                     'wanted' : 2})
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" in content
        assert "Ron Weasley" not in content

    def test_search_for_one_instructor_near_airport(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_55_105.id,
                                     'wanted' : 1})
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" not in content
        assert "Harry Potter" not in content
        assert "Ron Weasley" in content

    def test_search_for_one_instructor_near_latlong(self):
        response = self.client.post(reverse('instructors'),
                                    {'latitude' : 5,
                                     'longitude' : 45,
                                     'wanted' : 1})
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" not in content
        assert "Harry Potter" in content
        assert "Ron Weasley" not in content

    def test_non_instructors_not_returned_by_search(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_0_0.id,
                                     'wanted' : 1000})
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" in content
        assert "Ron Weasley" in content

    def test_match_instructors_on_one_skill(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_50_100.id,
                                     'Git' : 'on',
                                     'wanted' : 1000})
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" not in content
        assert "Ron Weasley" in content

    def test_match_instructors_on_two_skills(self):
        response = self.client.post(reverse('instructors'),
                                    {'airport' : self.airport_50_100.id,
                                     'Git' : 'on',
                                     'SQL' : 'on',
                                     'wanted' : 1000})
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" not in content
        assert "Ron Weasley" not in content
