from django.core.urlresolvers import reverse
from .base import TestBase


class TestLocateInstructors(TestBase):
    '''Test cases for locating instructors.'''

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_non_instructors_not_returned_by_search(self):
        response = self.client.get(
            reverse('instructors'),
            {'airport_1': self.airport_0_0.pk, 'submit': 'Submit'}
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" in content
        assert "Ron Weasley" in content

    def test_match_instructors_on_one_skill(self):
        response = self.client.get(
            reverse('instructors'),
            {'airport_1': self.airport_50_100.pk, 'lessons': [self.git.pk],
             'submit': 'Submit'}
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" not in content
        assert "Ron Weasley" in content

    def test_match_instructors_on_two_skills(self):
        response = self.client.get(
            reverse('instructors'),
            {'airport_1': self.airport_50_100.pk,
             'lessons': [self.git.pk, self.sql.pk],
             'submit': 'Submit'}
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" not in content
        assert "Ron Weasley" not in content

    def test_match_by_country(self):
        response = self.client.get(
            reverse('instructors'),
            {'country': ['AL'], 'submit': 'Submit'}
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" not in content
        assert "Ron Weasley" not in content

    def test_match_by_multiple_countries(self):
        response = self.client.get(
            reverse('instructors'),
            {'country': ['AL', 'BG'], 'submit': 'Submit'}
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" in content
        assert "Ron Weasley" not in content

    def test_match_gender(self):
        response = self.client.get(
            reverse('instructors'),
            {'latitude': 1, 'longitude': 1, 'gender': 'F', 'submit': 'Submit'}
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" in content
        assert "Harry Potter" not in content
        assert "Ron Weasley" not in content

        response = self.client.get(
            reverse('instructors'),
            {'latitude': 1, 'longitude': 1, 'gender': 'M', 'submit': 'Submit'}
        )
        assert response.status_code == 200
        content = response.content.decode('utf-8')
        assert "Hermione Granger" not in content
        assert "Harry Potter" in content
        assert "Ron Weasley" in content
