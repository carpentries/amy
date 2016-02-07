from django.core.urlresolvers import reverse
from django.core import mail

from .base import TestBase
from ..models import EventRequest, Event, Host
from ..forms import SWCEventRequestForm, DCEventRequestForm


class TestSWCEventRequestForm(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

    def test_fields_presence(self):
        """Test if the form shows correct fields."""
        form = SWCEventRequestForm()
        fields_left = set(form.fields.keys())
        fields_right = set([
            'name', 'email', 'affiliation', 'location', 'country',
            'conference', 'preferred_date', 'language', 'workshop_type',
            'approx_attendees', 'attendee_domains', 'attendee_domains_other',
            'attendee_academic_levels', 'attendee_computing_levels',
            'cover_travel_accomodation', 'understand_admin_fee',
            'travel_reimbursement', 'travel_reimbursement_other',
            'admin_fee_payment', 'comment', 'captcha',
        ])
        assert fields_left == fields_right

    def test_request_added(self):
        """Ensure the request is successfully added to the pool."""
        data = {
            'workshop_type': 'swc',
            'recaptcha_response_field': 'PASSED',  # to auto-pass RECAPTCHA
            'name': 'Harry Potter', 'email': 'harry@potter.com',
            'affiliation': 'Hogwarts', 'location': 'United Kingdom',
            'country': 'GB', 'preferred_date': 'soon',
            'approx_attendees': '20-40',
            'attendee_domains': [1, 2],  # IDs
            'attendee_domains_other': 'Nonsesology',
            'attendee_academic_levels': [1, 2],  # IDs
            'attendee_computing_levels': [1, 2],  # IDs
            'cover_travel_accomodation': True,
            'understand_admin_fee': True,
            'travel_reimbursement': 'book', 'travel_reimbursement_other': '',
            'admin_fee_payment': 'self-organized', 'comment': '',
        }
        rv = self.client.post(reverse('swc_workshop_request'), data)
        assert rv.status_code == 200
        content = rv.content.decode('utf-8')
        assert 'Fix errors below' not in content
        assert 'Thank you for requesting a workshop' in content
        assert EventRequest.objects.all().count() == 1
        assert EventRequest.objects.all()[0].active is True
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        self.assertEqual(
            msg.subject,
            '[SWC] New workshop request: Hogwarts, United Kingdom'
        )

    def test_request_discarded(self):
        """Ensure the request is discarded properly."""
        # add a minimal request
        er = EventRequest.objects.create(
            name='Harry Potter', email='harry@potter.com',
            affiliation='Hogwarts', location='United Kingdom',
            country='GB', workshop_type='swc',
        )
        rv = self.client.get(reverse('eventrequest_discard', args=[er.pk]))
        assert rv.status_code == 302
        er.refresh_from_db()
        assert not er.active


class TestDCEventRequestForm(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

    def test_fields_presence(self):
        """Test if the form shows correct fields."""
        form = DCEventRequestForm()
        fields_left = set(form.fields.keys())
        fields_right = set([
            'name', 'email', 'affiliation', 'location', 'country',
            'conference', 'preferred_date', 'language', 'workshop_type',
            'approx_attendees', 'attendee_domains', 'attendee_domains_other',
            'data_types', 'data_types_other', 'attendee_academic_levels',
            'attendee_data_analysis_level', 'cover_travel_accomodation',
            'understand_admin_fee', 'fee_waiver_request',
            'travel_reimbursement', 'travel_reimbursement_other',
            'comment', 'captcha',
        ])
        assert fields_left == fields_right

    def test_request_added(self):
        """Ensure the request is successfully added to the pool."""
        data = {
            'workshop_type': 'dc',
            'recaptcha_response_field': 'PASSED',  # to auto-pass RECAPTCHA
            'name': 'Harry Potter', 'email': 'harry@potter.com',
            'affiliation': 'Hogwarts', 'location': 'United Kingdom',
            'country': 'GB', 'preferred_date': 'soon',
            'approx_attendees': '20-40',
            'attendee_domains': [1, 2],  # IDs
            'attendee_domains_other': 'Nonsesology',
            'data_types': 'survey', 'data_types_other': '',
            'attendee_academic_levels': [1, 2],  # IDs
            'attendee_data_analysis_level': [1, 2],  # IDs
            'cover_travel_accomodation': True,
            'understand_admin_fee': True, 'fee_waiver_request': True,
            'travel_reimbursement': 'book', 'travel_reimbursement_other': '',
            'comment': '',
        }
        rv = self.client.post(reverse('dc_workshop_request'), data)
        assert rv.status_code == 200
        content = rv.content.decode('utf-8')
        assert 'Fix errors below' not in content
        assert 'Thank you for requesting a workshop' in content
        assert EventRequest.objects.all().count() == 1
        assert EventRequest.objects.all()[0].active is True
        assert len(mail.outbox) == 1
        msg = mail.outbox[0]
        self.assertEqual(
            msg.subject,
            '[DC] New workshop request: Hogwarts, United Kingdom'
        )

    def test_request_discarded(self):
        """Ensure the request is discarded properly."""
        # add a minimal request
        er = EventRequest.objects.create(
            name='Harry Potter', email='harry@potter.com',
            affiliation='Hogwarts', location='United Kingdom',
            country='GB', workshop_type='dc',
        )
        rv = self.client.get(reverse('eventrequest_discard', args=[er.pk]))
        assert rv.status_code == 302
        er.refresh_from_db()
        assert not er.active


class TestEventRequestsViews(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

        self.er1 = EventRequest.objects.create(
            active=True, name="Harry Potter", email="harry@potter.com",
            affiliation="Hogwarts", location="Scotland", country="GB",
            preferred_date="soon",
        )
        self.er2 = EventRequest.objects.create(
            active=False, name="Harry Potter", email="harry@potter.com",
            affiliation="Hogwarts", location="Scotland", country="GB",
            preferred_date="soon",
        )

    def test_active_requests_list(self):
        rv = self.client.get(reverse('all_eventrequests'))
        assert self.er1 in rv.context['requests']
        assert self.er2 not in rv.context['requests']

    def test_inactive_requests_list(self):
        rv = self.client.get(reverse('all_eventrequests') + '?active=false')
        assert self.er1 not in rv.context['requests']
        assert self.er2 in rv.context['requests']

    def test_active_request_view(self):
        rv = self.client.get(reverse('eventrequest_details',
                                     args=[self.er1.pk]))
        assert rv.status_code == 200

    def test_inactive_request_view(self):
        rv = self.client.get(reverse('eventrequest_details',
                                     args=[self.er2.pk]))
        assert rv.status_code == 200

    def test_active_request_accept(self):
        rv = self.client.get(reverse('eventrequest_accept',
                                     args=[self.er1.pk]))
        assert rv.status_code == 200

    def test_active_request_accepted(self):
        """Ensure a backlink from Event to EventRequest that created the
        event exists after ER is accepted."""
        data = {
            'slug': 'test-event',
            'host_1': Host.objects.first().pk,
            'tags': [1],
        }
        rv = self.client.post(
            reverse('eventrequest_accept', args=[self.er1.pk]),
            data)
        assert rv.status_code == 302, rv.status_code
        self.assertEqual(Event.objects.get(slug='test-event').request,
                         self.er1)

    def test_inactive_request_accept(self):
        rv = self.client.get(reverse('eventrequest_accept',
                                     args=[self.er2.pk]))
        assert rv.status_code != 200

    def test_active_request_discard(self):
        rv = self.client.get(reverse('eventrequest_discard',
                                     args=[self.er1.pk]), follow=True)
        assert rv.status_code == 200

    def test_inactive_request_discard(self):
        rv = self.client.get(reverse('eventrequest_discard',
                                     args=[self.er2.pk]), follow=True)
        assert rv.status_code != 200
