import unittest

from django.core import mail
from django.urls import reverse

from .base import TestBase
from ..forms import EventSubmitForm
from ..models import EventSubmission, Organization, Tag


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

    @unittest.skip('Event submission disabled as per @maneesha\'s request.')
    def test_submission_added(self):
        """Test if the submitted form adds a new event submission."""
        self.assertEqual(len(EventSubmission.objects.all()), 1)
        data = {
            'g-recaptcha-response': 'PASSED',
            'contact_name': 'Harry Potter',
            'contact_email': 'harry@potter.com',
            'self_organized': True,
            'url': 'http://example.org/2016-02-13-Howart',
            'notes': '',
            'privacy_consent': True,
        }
        rv = self.client.post(reverse('event_submit'), data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertNotIn('form', rv.context)
        self.assertEqual(len(EventSubmission.objects.all()), 2)

    @unittest.skip('Event submission disabled as per @maneesha\'s request.')
    def test_submission_sends_email(self):
        """Test if the submitted form results in email sent."""
        data = {
            'g-recaptcha-response': 'PASSED',
            'contact_name': 'Harry Potter',
            'contact_email': 'harry@potter.com',
            'self_organized': True,
            'url': 'http://example.org/2016-02-13-Hogwart',
            'notes': '',
            'privacy_consent': True,
        }
        rv = self.client.post(reverse('event_submit'), data,
                              follow=True)
        self.assertEqual(rv.status_code, 200)
        self.assertNotIn('form', rv.context)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(
            msg.subject,
            'New workshop submission from Harry Potter'
        )

    def test_request_accepted(self):
        """Ensure submission is turned inactive after acceptance."""
        self.assertEqual(self.submission.active, True)
        minimal_event = {
            'slug': '1970-01-01-first-event',
            'host': Organization.objects.first().pk,
            'tags': [Tag.objects.first().pk],
            'invoice_status': 'not-invoiced',
        }
        rv = self.client.post(reverse('eventsubmission_accept',
                                      args=[self.submission.pk]),
                              minimal_event, follow=True)
        self.assertEqual(rv.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.active, False)

    def test_request_discarded(self):
        """Ensure submission is turned inactive after being discarded."""
        self.assertEqual(self.submission.active, True)
        rv = self.client.get(reverse('eventsubmission_discard',
                                     args=[self.submission.pk]), follow=True)
        self.assertEqual(rv.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.active, False)
