from django.test import TestCase
from ..models import Site


class TestSiteNotes(TestCase):
    """Make sure notes once written are saved forever!"""

    def test_site_without_notes(self):
        "Make sure sites without notes don't have NULLed field ``notes``"
        s = Site(domain="example.org",
                 fullname="Sample Example",
                 country="US")

        # test for field's default value (the field is not NULL)
        self.assertEqual(s.notes, "")  # therefore the field is not NULL

    def test_site_with_notes(self):
        "Make sure event with notes are correctly stored"

        notes = "This site is untrusted."

        s = Site(domain="example.org",
                 fullname="Sample Example",
                 country="US",
                 notes=notes)

        # make sure that notes have been saved
        self.assertEqual(s.notes, notes)
