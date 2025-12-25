from django.urls import reverse

from src.consents.models import Consent, Term, TermEnum
from src.workshops.models import KnowledgeDomain, Person, Qualification
from src.workshops.tests.base import TestBase


class TestAutoUpdateProfile(TestBase):
    def setUp(self) -> None:
        self._setUpLessons()
        self._setUpLanguages()

        self.user = Person.objects.create_user(
            username="user",
            personal="",
            family="",
            email="user@example.org",
            password="pass",
        )

        self.person_consent_required_terms(self.user)

        Qualification.objects.create(person=self.user, lesson=self.git)
        Qualification.objects.create(person=self.user, lesson=self.sql)

        self.physics = KnowledgeDomain.objects.create(name="physics")
        self.chemistry = KnowledgeDomain.objects.create(name="chemistry")
        self.user.domains.add(self.physics)

        self.user.languages.add(self.english)
        self.user.languages.add(self.french)

        self.client.login(username="user", password="pass")

    def test_load_form(self) -> None:
        rv = self.client.get(reverse("autoupdate_profile"))
        self.assertEqual(rv.status_code, 200)

    def test_update_profile(self) -> None:
        term_slugs = [
            TermEnum.MAY_CONTACT,
            TermEnum.MAY_PUBLISH_NAME,
            TermEnum.PUBLIC_PROFILE,
        ]
        terms_by_term_slug = {
            term.slug: term for term in Term.objects.filter(slug__in=term_slugs).active().prefetch_active_options()
        }
        consent_data = {
            f"consents-{slug}": terms_by_term_slug[slug].active_options[0].pk
            for slug in term_slugs  # type: ignore
        }
        data = {
            "personal": "admin",
            "middle": "",
            "family": "Smith",
            "email": "admin@example.org",
            "gender": Person.UNDISCLOSED,
            "airport_iata": "CDG",
            "country": "PL",
            "timezone": "Europe/Warsaw",
            "github": "changed",
            "twitter": "",
            "bluesky": "",
            "mastodon": "",
            "url": "",
            "username": "changed",
            "affiliation": "",
            "languages": [self.latin.pk, self.french.pk],
            "domains": [self.chemistry.pk],
            "lessons": [self.git.pk, self.matlab.pk],
            "consents-person": self.user.pk,
            **consent_data,
        }

        rv = self.client.post(reverse("autoupdate_profile"), data, follow=True)
        self.assertEqual(rv.status_code, 200)
        content = rv.content.decode("utf-8")
        self.assertNotIn("Fix errors below", content)
        self.user.refresh_from_db()

        self.assertEqual(self.user.username, "user")  # username is read-only
        self.assertEqual(self.user.github, None)  # github is read-only
        self.assertEqual(self.user.family, "Smith")
        self.assertEqual(set(self.user.lessons.all()), {self.git, self.matlab})
        self.assertEqual(list(self.user.domains.all()), [self.chemistry])
        self.assertEqual(set(self.user.languages.all()), {self.french, self.latin})

        updated_consents_by_term_slug = {
            consent.term.slug: consent
            for consent in Consent.objects.filter(term__slug__in=term_slugs, person=self.user)
            .active()
            .select_related("term")
        }
        for slug in term_slugs:
            self.assertEqual(
                updated_consents_by_term_slug[slug].term_option.pk,  # type: ignore
                consent_data[f"consents-{slug}"],
            )
