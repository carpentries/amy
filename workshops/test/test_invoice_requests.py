from datetime import date

from .base import TestBase
from ..models import InvoiceRequest, Event, Host
from ..forms import InvoiceRequestForm


class TestInvoiceRequestForm(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

    def test_adding_minimal(self):
        """Test submitting a minimalistic form ends up in
        Event.invoicerequest_set."""
        event = Event.objects.create(
            slug='invoiceable-event', host=Host.objects.first(),
            start='2016-02-09', admin_fee=2500,
            venue='School of Science',
        )
        data = {
            'organization': event.host.pk,
            'reason': 'admin-fee',
            'date': event.start,
            'event': event.pk,
            'event_location': event.venue,
            'contact_name': 'dr Jane Smith',
            'contact_email': 'jane.smith@ufl.edu',
            'full_address': 'dr Jane Smith, University of Florida',
            'amount': event.admin_fee,
            'vendor_form_required': 'no',
            'receipts_sent': 'not-yet',
        }
        form = InvoiceRequestForm(data)
        self.assertTrue(form.is_valid())
        self.assertEqual(event.invoicerequest_set.count(), 0)
        form.save()
        self.assertEqual(event.invoicerequest_set.count(), 1)


class TestInvoiceRequest(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

    def test_status_repr(self):
        """Test if InvoiceRequest long status representation is fine."""
        day = date(2016, 2, 9)
        event = Event.objects.create(
            slug='invoiceable-event', host=Host.objects.first(),
            start=day, admin_fee=2500,
            venue='School of Science',
        )
        request = InvoiceRequest.objects.create(
            organization=event.host, date=event.start,
            event=event, event_location=event.venue,
            contact_name='dr Jane Smith', contact_email='jane.smith@ufl.edu',
            full_address='dr Jane Smith, University of Florida',
            amount=event.admin_fee, form_W9=False,
            sent_date=day, paid_date=day,
        )

        tests = [
            ('not-invoiced', 'Not invoiced'),
            ('sent', 'Sent out on 2016-02-09'),
            ('paid', 'Paid on 2016-02-09'),
        ]

        for status, long_status in tests:
            with self.subTest(status=status):
                request.status = status
                # request.save()
                self.assertEqual(request.long_status, long_status)
