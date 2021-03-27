from consents.models import Consent, Term, TermOption
from django.urls import reverse
from django_webtest import WebTest
from rest_framework import status
from workshops.models import Person


class ConsentsUpdateTest(WebTest):
    def setUp(self):
        super().setUp()
        self.person = Person.objects.create(
            personal="Harry", family="Potter", email="hp@magic.uk"
        )

    def test_consents_update(self):
        """
        Ensures the ConsentsUpdate view is able to show
        and save all active terms whether consents exist or not.
        """
        term1 = Term.objects.create(content="term1", slug="term1")
        term1_option1 = TermOption.objects.create(
            term=term1,
            option_type=TermOption.AGREE,
            content="term1_option1",
        )
        TermOption.objects.create(
            term=term1,
            option_type=TermOption.AGREE,
            content="term1_option2",
        )
        term2 = Term.objects.create(content="term2", slug="term2")
        TermOption.objects.create(
            term=term2,
            option_type=TermOption.AGREE,
        )
        term2_option2 = TermOption.objects.create(
            term=term2,
            option_type=TermOption.DECLINE,
        )
        # Currently can only be called via redirect
        # from the PersonUpdate view. No direct consent edit view.
        person_edit_view = reverse("person_edit", kwargs={"person_id": self.person.pk})
        data = {
            "consents-person": self.person.pk,
            f"consents-{term1.slug}": term1_option1.pk,
            f"consents-{term2.slug}": term2_option2.pk,
        }
        consents_path = reverse("consents_add", kwargs={"person_id": self.person.pk})
        result = self.client.post(f"{consents_path}?next={person_edit_view}", data)
        self.assertEquals(result.status_code, status.HTTP_302_FOUND)
        consents = Consent.objects.filter(person=self.person).active()
        self.assertEqual(len(consents), 2)
        self.assertEqual(consents.filter(term=term1)[0].term_option, term1_option1)
        self.assertEqual(consents.filter(term=term2)[0].term_option, term2_option2)
