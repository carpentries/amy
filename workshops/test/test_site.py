from ..models import Site
from .base import TestBase


class TestSiteNotes(TestBase):
    '''Test cases for Site notes.'''

    def test_fixture_notes(self):
        assert self.site_alpha.notes == '', \
            'Alpha Site notes should be empty'
        assert self.site_beta.notes == 'Notes\nabout\nBrazil\n', \
            'Beta Site notes incorrect'

    def test_site_created_without_notes(self):
        s = Site(domain='example.org',
                 fullname='Sample Example',
                 country='United-States')
        assert s.notes == '', \
            'Site created without notes should have empty notes'
