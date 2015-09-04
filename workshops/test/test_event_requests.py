from django.core.urlresolvers import reverse
from django.test import TestCase

from .base import TestBase
from ..models import EventRequest, AcademicLevel, ComputingExperienceLevel
from ..forms import SwCEventRequestForm, DCEventRequestForm


class TestSwCEventRequestForm(TestBase):
    def test_fields_presence(self):
        """Test if the form shows correct fields."""
        form = SwCEventRequestForm()
        fields_left = set(form.fields.keys())
        fields_right = set([
            'name', 'email', 'affiliation', 'location', 'country',
            'conference', 'preferred_date', 'workshop_type',
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
            'attendee_domains': [], 'attendee_domains_other': 'Nonsesology',
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
        assert 'Thank you for requesting a workshop' in content
        assert EventRequest.objects.all().count() == 1
        assert EventRequest.objects.all()[0].active is True


class TestDCEventRequestForm(TestCase):
    def test_fields_presence(self):
        """Test if the form shows correct fields."""
        form = DCEventRequestForm()
        fields_left = set(form.fields.keys())
        fields_right = set([
            'name', 'email', 'affiliation', 'location', 'country',
            'conference', 'preferred_date', 'workshop_type',
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
            'attendee_domains': [], 'attendee_domains_other': 'Nonsesology',
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
        assert 'Thank you for requesting a workshop' in content
        assert EventRequest.objects.all().count() == 1
        assert EventRequest.objects.all()[0].active is True
