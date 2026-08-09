from datetime import date, timedelta

from django.test import override_settings
from django.urls import reverse

from src.fiscal.models import Partnership, PartnershipTier
from src.offering.models import Account, AccountBenefit, AccountOwner, Benefit
from src.workshops.models import Event, Organization, Person, Role, Task
from src.workshops.tests.base import TestBase

FLAG_DISABLED = {"SERVICE_OFFERING": [("boolean", False)]}


class TestUserPartnerships(TestBase):
    """Tests for the read-only partnership page available to account owners."""

    def setUp(self) -> None:
        super().setUp()

        self.url = reverse("user-partnerships")
        self.today = date.today()

        self.user = Person.objects.create_user(
            username="owner",
            personal="Account",
            family="Owner",
            email="owner@example.org",
            password="pass",
        )
        self.person_consent_required_terms(self.user)
        self.client.login(username="owner", password="pass")

        self.organisation = Organization.objects.create(fullname="Owned Org", domain="owned.example.org")
        self.account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=self.organisation,
        )
        AccountOwner.objects.create(
            account=self.account,
            person=self.user,
            permission_type="owner",
        )

        self.tier = PartnershipTier.objects.create(name="Gold", credits=100)
        self.partnership = Partnership.objects.create(
            name="Owned Org partnership",
            tier=self.tier,
            credits=100,
            account=self.account,
            partner_organisation=self.organisation,
            agreement_start=self.today - timedelta(days=30),
            agreement_end=self.today + timedelta(days=335),
            agreement_link="https://example.org/agreement",
            registration_code="OWNED-ORG-2026",
        )

        self.seat_benefit = Benefit.objects.create(
            name="Training seat",
            description="A single training seat",
            unit_type="seat",
            credits=1,
        )
        self.event_benefit = Benefit.objects.create(
            name="Centrally-organised workshop",
            description="A single workshop",
            unit_type="event",
            credits=10,
        )
        self.seat_account_benefit = AccountBenefit.objects.create(
            account=self.account,
            partnership=self.partnership,
            benefit=self.seat_benefit,
            start_date=self.partnership.agreement_start,
            end_date=self.partnership.agreement_end,
            allocation=6,
        )
        self.event_account_benefit = AccountBenefit.objects.create(
            account=self.account,
            partnership=self.partnership,
            benefit=self.event_benefit,
            start_date=self.partnership.agreement_start,
            end_date=self.partnership.agreement_end,
            allocation=2,
        )

    def _create_individual_account(self) -> Account:
        """Create an individual account owned by `self.user`, as `AccountCreate` does."""
        account = Account.objects.create(
            account_type=Account.AccountTypeChoices.INDIVIDUAL,
            generic_relation=self.user,
        )
        AccountOwner.objects.create(account=account, person=self.user, permission_type="owner")
        return account

    def _use_seats(self, count: int) -> None:
        """Allocate `count` seats of `self.seat_account_benefit` to tasks."""
        event = Event.objects.create(slug="2026-01-01-test", host=self.organisation)
        role = Role.objects.create(name="learner", verbose_name="Learner")
        for i in range(count):
            person = Person.objects.create(
                username=f"learner{i}",
                personal="Learner",
                family=str(i),
                email=f"learner{i}@example.org",
            )
            Task.objects.create(
                event=event,
                person=person,
                role=role,
                allocated_benefit=self.seat_account_benefit,
            )

    def test_login_required(self) -> None:
        # Arrange
        self.client.logout()

        # Act
        rv = self.client.get(self.url)

        # Assert
        self.assertEqual(rv.status_code, 302)

    @override_settings(FLAGS=FLAG_DISABLED)
    def test_page_unavailable_when_flag_disabled(self) -> None:
        # Act
        rv = self.client.get(self.url)

        # Assert
        self.assertEqual(rv.status_code, 404)

    def test_page_unavailable_for_person_who_is_not_an_account_owner(self) -> None:
        # Arrange
        AccountOwner.objects.filter(person=self.user).delete()

        # Act
        rv = self.client.get(self.url)

        # Assert
        self.assertEqual(rv.status_code, 404)

    def test_page_unavailable_for_inactive_owner(self) -> None:
        # Arrange
        AccountOwner.objects.filter(person=self.user).update(active=False)

        # Act
        rv = self.client.get(self.url)

        # Assert
        self.assertEqual(rv.status_code, 404)

    def test_page_unavailable_when_account_is_inactive(self) -> None:
        # Arrange
        Account.objects.filter(pk=self.account.pk).update(active=False)

        # Act
        rv = self.client.get(self.url)

        # Assert
        self.assertEqual(rv.status_code, 404)

    def test_page_unavailable_for_owner_of_individual_account_only(self) -> None:
        # Arrange
        AccountOwner.objects.filter(person=self.user).delete()
        self._create_individual_account()

        # Act
        rv = self.client.get(self.url)

        # Assert
        self.assertEqual(rv.status_code, 404)

    def test_individual_account_not_displayed(self) -> None:
        """Owning an individual account on top of an organisation account doesn't add it
        to the page."""
        # Arrange
        individual_account = self._create_individual_account()

        # Act
        rv = self.client.get(self.url)

        # Assert
        (summary,) = rv.context["account_summaries"]
        self.assertEqual(summary.account, self.account)
        self.assertNotEqual(summary.account, individual_account)

    def test_page_displays_partnership_details(self) -> None:
        # Act
        rv = self.client.get(self.url)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, "Owned Org partnership")
        self.assertContains(rv, "OWNED-ORG-2026")
        self.assertContains(rv, "https://example.org/agreement")
        self.assertContains(rv, "Gold")

    def test_page_displays_account_benefits(self) -> None:
        # Act
        rv = self.client.get(self.url)

        # Assert
        self.assertContains(rv, "Training seat")
        self.assertContains(rv, "Centrally-organised workshop")

    def test_page_is_read_only(self) -> None:
        """No links to admin-only views are rendered."""
        # Act
        rv = self.client.get(self.url)

        # Assert
        content = rv.content.decode("utf-8")
        self.assertNotIn(self.partnership.get_absolute_url(), content)
        self.assertNotIn(self.account.get_absolute_url(), content)
        self.assertNotIn(self.seat_account_benefit.get_absolute_url(), content)
        self.assertNotIn(reverse("account-benefit-create"), content)

    def test_stats(self) -> None:
        # Arrange
        self._use_seats(2)

        # Act
        rv = self.client.get(self.url)

        # Assert
        (summary,) = rv.context["account_summaries"]
        self.assertEqual(summary.account, self.account)
        self.assertEqual(summary.permission_types, ["Owner"])
        self.assertEqual(summary.stats.credits_allowed, 100)
        self.assertEqual(summary.stats.credits_used, 6 * 1 + 2 * 10)
        self.assertEqual(summary.stats.seats_allocated, 6)
        self.assertEqual(summary.stats.seats_used, 2)
        self.assertEqual(summary.stats.seats_remaining, 4)
        self.assertEqual(summary.stats.events_allocated, 2)
        self.assertEqual(summary.stats.events_used, 0)
        self.assertEqual(summary.stats.events_remaining, 2)
        self.assertEqual(summary.stats.benefits_total, 2)
        self.assertEqual(summary.stats.benefits_active, 2)

    def test_stats_dont_count_inactive_benefits(self) -> None:
        # Arrange
        AccountBenefit.objects.filter(pk=self.event_account_benefit.pk).update(
            start_date=self.today - timedelta(days=730),
            end_date=self.today - timedelta(days=365),
        )

        # Act
        rv = self.client.get(self.url)

        # Assert
        (summary,) = rv.context["account_summaries"]
        self.assertEqual(summary.stats.benefits_total, 2)
        self.assertEqual(summary.stats.benefits_active, 1)

    def test_per_benefit_usage(self) -> None:
        # Arrange
        self._use_seats(2)

        # Act
        rv = self.client.get(self.url)

        # Assert
        (summary,) = rv.context["account_summaries"]
        usage = {
            benefit_summary.account_benefit.pk: (benefit_summary.used, benefit_summary.remaining)
            for benefit_summary in summary.account_benefits
        }
        self.assertEqual(usage[self.seat_account_benefit.pk], (2, 4))
        self.assertEqual(usage[self.event_account_benefit.pk], (0, 2))

    def test_other_accounts_not_displayed(self) -> None:
        """Partnerships of accounts the user doesn't own are not shown."""
        # Arrange
        other_organisation = Organization.objects.create(fullname="Other Org", domain="other.example.org")
        other_account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=other_organisation,
        )
        Partnership.objects.create(
            name="Other Org partnership",
            tier=self.tier,
            credits=50,
            account=other_account,
            partner_organisation=other_organisation,
            agreement_start=self.today,
            agreement_end=self.today + timedelta(days=365),
            agreement_link="https://example.org/other-agreement",
            registration_code="OTHER-ORG-2026",
        )

        # Act
        rv = self.client.get(self.url)

        # Assert
        self.assertNotContains(rv, "Other Org partnership")
        self.assertEqual(len(rv.context["account_summaries"]), 1)

    def test_multiple_owned_accounts(self) -> None:
        # Arrange
        second_organisation = Organization.objects.create(fullname="Second Org", domain="second.example.org")
        second_account = Account.objects.create(
            account_type=Account.AccountTypeChoices.ORGANISATION,
            generic_relation=second_organisation,
        )
        AccountOwner.objects.create(
            account=second_account,
            person=self.user,
            permission_type="billing_contact",
        )

        # Act
        rv = self.client.get(self.url)

        # Assert
        summaries = rv.context["account_summaries"]
        self.assertEqual(len(summaries), 2)
        self.assertEqual(
            [summary.permission_types for summary in summaries],
            [["Owner"], ["Billing Contact"]],
        )

    def test_navigation_link_displayed_for_account_owner(self) -> None:
        # Act
        rv = self.client.get(reverse("user-dashboard"))

        # Assert
        self.assertContains(rv, "Your partnerships")
        self.assertContains(rv, self.url)

    def test_navigation_link_not_displayed_for_non_owner(self) -> None:
        # Arrange
        AccountOwner.objects.filter(person=self.user).delete()

        # Act
        rv = self.client.get(reverse("user-dashboard"))

        # Assert
        self.assertNotContains(rv, "Your partnerships")

    def test_navigation_link_not_displayed_for_owner_of_individual_account_only(self) -> None:
        # Arrange
        AccountOwner.objects.filter(person=self.user).delete()
        self._create_individual_account()

        # Act
        rv = self.client.get(reverse("user-dashboard"))

        # Assert
        self.assertNotContains(rv, "Your partnerships")

    @override_settings(FLAGS=FLAG_DISABLED)
    def test_navigation_link_not_displayed_when_flag_disabled(self) -> None:
        # Act
        rv = self.client.get(reverse("user-dashboard"))

        # Assert
        self.assertNotContains(rv, "Your partnerships")
