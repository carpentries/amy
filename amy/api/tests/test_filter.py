from typing import Any, Dict

from django.urls import reverse
from rest_framework.test import APITestCase

from consents.models import Consent, Term, TermOption
from workshops.models import Airport, Person


class TestFilter(APITestCase):
    def setUp(self):
        def get_option(term_slug: str, option_type: str) -> TermOption:
            return [
                option
                for option in terms_dict[term_slug].options
                if option.option_type == option_type
            ][0]

        def get_consent(term_slug: str, person: Person) -> Consent:
            return [
                consent
                for consent in old_consents
                if consent.term.slug == term_slug and consent.person == person
            ][0]

        self.admin_1 = Person.objects.create_superuser(
            username="admin1",
            personal="Super",
            family="User",
            email="sudo1@example.org",
            password="admin",
        )
        self.admin_1.data_privacy_agreement = True
        self.admin_1.airport = Airport.objects.first()
        self.admin_1.save()

        self.admin_2 = Person.objects.create_superuser(
            username="admin_2",
            personal="Super",
            family="User",
            email="sudo@example.org",
            password="admin",
        )
        self.admin_2.data_privacy_agreement = True
        self.admin_2.airport = Airport.objects.first()
        self.admin_2.save()

        terms = (
            Term.objects.filter(slug__in=["may-contact", "public-profile"])
            .active()
            .prefetch_active_options()
        )
        terms_dict = {term.slug: term for term in terms}
        may_contact_agree = get_option("may-contact", TermOption.AGREE)
        may_contact_decline = get_option("may-contact", TermOption.DECLINE)
        publish_profile_agree = get_option("public-profile", TermOption.AGREE)
        publish_profile_decline = get_option("public-profile", TermOption.DECLINE)

        old_consents = (
            Consent.objects.filter(
                person__in=[self.admin_1, self.admin_2],
                term__slug__in=["may-contact", "public-profile"],
            )
            .active()
            .select_related("term", "person")
        )

        Consent.reconsent(
            consent=get_consent("may-contact", self.admin_1),
            term_option=may_contact_agree,
        )
        Consent.reconsent(
            consent=get_consent("may-contact", self.admin_2),
            term_option=may_contact_decline,
        )
        Consent.reconsent(
            consent=get_consent("public-profile", self.admin_1),
            term_option=publish_profile_agree,
        )
        Consent.reconsent(
            consent=get_consent("public-profile", self.admin_2),
            term_option=publish_profile_decline,
        )

        self.client.login(username="admin1", password="admin")

    def test_person_filter(self):
        def assert_data(data: Dict[str, Any], expected_people) -> None:
            usernames = [person_data["username"] for person_data in data["results"]]
            self.assertCountEqual(
                usernames, [person.username for person in expected_people]
            )

        person_api_url = reverse("api:person-list")

        # no filter
        people_response = self.client.get(person_api_url)
        assert_data(people_response.data, [self.admin_1, self.admin_2])

        # publish profile
        people_response = self.client.get(f"{person_api_url}?&publish_profile=false")
        assert_data(people_response.data, [self.admin_2])

        people_response = self.client.get(f"{person_api_url}?&publish_profile=true")
        assert_data(people_response.data, [self.admin_1])

        # may contact
        people_response = self.client.get(f"{person_api_url}?&may_contact=false")
        assert_data(people_response.data, [self.admin_2])

        people_response = self.client.get(f"{person_api_url}?&may_contact=true")
        assert_data(people_response.data, [self.admin_1])

        # combined
        people_response = self.client.get(
            f"{person_api_url}?&may_contact=false&publish_profile=true"
        )
        assert_data(people_response.data, [])

        people_response = self.client.get(
            f"{person_api_url}?&may_contact=true&publish_profile=true"
        )
        assert_data(people_response.data, [self.admin_1])
