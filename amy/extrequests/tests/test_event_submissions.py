from django.urls import reverse

from extforms.deprecated_forms import EventSubmitForm
from workshops.models import EventSubmission, Organization, Tag, Event
from workshops.tests.base import TestBase


class TestEventSubmitForm(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()
        self.submission = EventSubmission.objects.create(
            url='http://example.org/2016-02-13-Hogwart',
            contact_name='Harry Potter', contact_email='harry@potter.com',
            self_organized=True)

    def test_exact_fields(self):
        """Test if the form shows correct fields."""
        form = EventSubmitForm()
        fields_left = list(form.fields.keys())
        fields_right = [
            'url', 'contact_name', 'contact_email',
            'self_organized', 'notes', 'privacy_consent', 'captcha',
        ]
        self.assertEqual(fields_left, fields_right)

    def test_submission_accepted_with_event(self):
        """Ensure submission is turned inactive after acceptance."""
        self.assertEqual(self.submission.state, "p")
        minimal_event = {
            'slug': '1970-01-01-first-event',
            'host': Organization.objects.first().pk,
            'tags': [Tag.objects.first().pk],
            'invoice_status': 'not-invoiced',
        }
        rv = self.client.post(reverse('eventsubmission_accept_event',
                                      args=[self.submission.pk]),
                              minimal_event, follow=True)
        self.assertEqual(rv.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, "a")
        self.assertEqual(
            Event.objects.get(slug='1970-01-01-first-event').eventsubmission,
            self.submission)

    def test_submission_discarded(self):
        """Ensure submission is turned inactive after being discarded."""
        self.assertEqual(self.submission.state, "p")
        rv = self.client.get(reverse('eventsubmission_set_state',
                                     args=[self.submission.pk, 'discarded']),
                             follow=True)
        self.assertEqual(rv.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, "d")

    def test_submission_accepted(self):
        """Ensure submission is turned inactive after being discarded."""
        self.assertEqual(self.submission.state, "p")
        rv = self.client.get(reverse('eventsubmission_set_state',
                                     args=[self.submission.pk, 'accepted']),
                             follow=True)
        self.assertEqual(rv.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, "a")

    def test_discarded_submission_reopened(self):
        self.submission.state = "d"
        self.submission.save()
        self.client.get(
            reverse('eventsubmission_set_state',
                    args=[self.submission.pk, 'pending']),
            follow=True)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, "p")

    def test_accepted_submission_reopened(self):
        self.submission.state = "a"
        self.submission.save()
        self.client.get(
            reverse('eventsubmission_set_state',
                    args=[self.submission.pk, 'pending']),
            follow=True)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.state, "p")
