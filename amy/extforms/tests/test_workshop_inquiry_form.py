from django.core import mail
from django.conf import settings
from django.urls import reverse

from extforms.forms import WorkshopInquiryRequestExternalForm
from extrequests.models import WorkshopInquiryRequest
from workshops.models import (
    Language,
    Curriculum,
    InfoSource,
)
from workshops.tests.base import TestBase


class TestWorkshopInquiryExternalForm(TestBase):
    """Test external (accessible to non-logged in users) form."""

    def test_fields_presence(self):
        """Test if the form shows correct fields."""
        form = WorkshopInquiryRequestExternalForm()
        fields_left = set(form.fields.keys())
        fields_right = set(
            [
                "personal",
                "family",
                "email",
                "secondary_email",
                "institution",
                "institution_other_name",
                "institution_other_URL",
                "institution_department",
                "location",
                "country",
                "routine_data",
                "routine_data_other",
                "domains",
                "domains_other",
                "academic_levels",
                "computing_levels",
                "audience_description",
                "requested_workshop_types",
                "preferred_dates",
                "other_preferred_dates",
                "language",
                "number_attendees",
                "administrative_fee",
                "travel_expences_management",
                "travel_expences_management_other",
                "travel_expences_agreement",
                "institution_restrictions",
                "institution_restrictions_other",
                "public_event",
                "public_event_other",
                "additional_contact",
                "carpentries_info_source",
                "carpentries_info_source_other",
                "user_notes",
                "data_privacy_agreement",
                "code_of_conduct_agreement",
                "host_responsibilities",
                "instructor_availability",
                "captcha",
            ]
        )
        self.assertEqual(fields_left, fields_right)

    def test_request_added(self):
        """Ensure the request is successfully added to the pool, and
        notification email is sent."""
        data = {
            "personal": "Harry",
            "family": "Potter",
            "email": "hpotter@magic.gov",
            "institution_other_name": "Ministry of Magic",
            "institution_other_URL": "magic.gov.uk",
            "location": "London",
            "country": "GB",
            "requested_workshop_types": [
                Curriculum.objects.get(slug="swc-python").pk,
                Curriculum.objects.get(slug="dc-ecology-r").pk,
            ],
            "preferred_dates": "",
            "other_preferred_dates": "03-04 November, 2018",
            "language": Language.objects.get(name="English").pk,
            "number_attendees": "10-40",
            "audience_description": "Students of Hogwarts",
            "administrative_fee": "waiver",
            "scholarship_circumstances": "Bugdet cuts in Ministry of Magic",
            "travel_expences_management": "booked",
            "travel_expences_management_other": "",
            "travel_expences_agreement": True,
            "institution_restrictions": "other",
            "institution_restrictions_other": "Only for wizards",
            "public_event": "closed",
            "public_event_other": "",
            "additional_contact": "",
            "carpentries_info_source": [InfoSource.objects.first().pk],
            "carpentries_info_source_other": "",
            "user_notes": "n/c",
            "data_privacy_agreement": True,
            "code_of_conduct_agreement": True,
            "host_responsibilities": True,
            "instructor_availability": True,
        }
        self.passCaptcha(data)

        rv = self.client.post(reverse("workshop_inquiry"), data, follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode("utf-8")
        if "form" in rv.context:
            self.assertEqual(
                rv.context["form"].is_valid(), True, dict(rv.context["form"].errors)
            )
        self.assertNotIn("Please fix errors in the form below", content)
        self.assertIn("Thank you for inquiring about The Carpentries", content)
        self.assertEqual(WorkshopInquiryRequest.objects.all().count(), 1)
        self.assertEqual(WorkshopInquiryRequest.objects.all()[0].state, "p")

        # 1 email for autoresponder, 1 email for admins
        self.assertEqual(len(mail.outbox), 2)

        # save the email messages for test debuggig
        # with open('email0.eml', 'wb') as f:
        #     f.write(mail.outbox[0].message().as_bytes())
        # with open('email1.eml', 'wb') as f:
        #     f.write(mail.outbox[1].message().as_bytes())

        # before tests, check if the template invalid string exists
        self.assertTrue(settings.TEMPLATES[0]["OPTIONS"]["string_if_invalid"])

        # test autoresponder email
        msg = mail.outbox[0]
        self.assertEqual(msg.subject, "Workshop inquiry confirmation")
        self.assertEqual(msg.recipients(), ["hpotter@magic.gov"])
        self.assertNotIn(
            settings.TEMPLATES[0]["OPTIONS"]["string_if_invalid"], msg.body
        )
        # test email for admins
        msg = mail.outbox[1]
        self.assertEqual(
            msg.subject,
            "New workshop inquiry: Ministry of Magic, 03-04 November, 2018",
        )
        self.assertEqual(msg.recipients(), ["admin-uk@carpentries.org"])
        self.assertNotIn(
            settings.TEMPLATES[0]["OPTIONS"]["string_if_invalid"], msg.body
        )
