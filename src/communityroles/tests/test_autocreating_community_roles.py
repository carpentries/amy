"""When an Award is created, it may automatically create Community Role(s)."""

from datetime import date

from django.urls import reverse

from src.communityroles.models import CommunityRole, CommunityRoleConfig
from src.workshops.models import Badge, Person
from src.workshops.tests.base import TestBase


class TestAutocreatingCommunityRoles(TestBase):
    def setUp(self) -> None:
        self.badge, _ = Badge.objects.get_or_create(name="instructor")
        self.config1 = CommunityRoleConfig.objects.create(
            name="test1",
            display_name="Test config 1",
            link_to_award=True,
            award_badge_limit=self.badge,
            autoassign_when_award_created=True,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        self.config2 = CommunityRoleConfig.objects.create(
            name="test2",
            display_name="Test config 2",
            link_to_award=True,
            award_badge_limit=self.badge,
            autoassign_when_award_created=True,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )

        # This config will not be used since it doesn't have autoassign
        self.config3 = CommunityRoleConfig.objects.create(
            name="test3",
            display_name="Test config 3",
            link_to_award=True,
            award_badge_limit=self.badge,
            autoassign_when_award_created=False,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )

        self.person = Person.objects.create(
            personal="Test",
            family="Family",
            email="test.person@example.org",
        )
        self.url = reverse("award_add")

        self._setUpUsersAndLogin()

    def test_autoassign(self) -> None:
        # Arrange
        data = {
            "award-person": self.person.pk,
            "award-badge": self.badge.pk,
            "award-awarded": "2022-09-19",
        }

        # Act
        result = self.client.post(self.url, data)

        # Assert
        self.assertEqual(result.status_code, 302)
        roles = CommunityRole.objects.filter(person=self.person)
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0].config, self.config1)
        self.assertEqual(roles[1].config, self.config2)
        self.assertEqual(roles[0].start, date.today())
        self.assertEqual(roles[1].start, date.today())
        self.assertEqual(roles[0].end, None)
        self.assertEqual(roles[1].end, None)

    def test_autoassign_considers_concurrent_roles(self) -> None:
        # Arrange
        CommunityRole.objects.create(
            config=self.config1,
            person=self.person,
            award=None,
            start=date(2022, 9, 1),
            end=None,
            inactivation=None,
            membership=None,
            url="",
        )
        data = {
            "award-person": self.person.pk,
            "award-badge": self.badge.pk,
            "award-awarded": "2022-09-19",
        }

        # Act
        result = self.client.post(self.url, data)

        # Assert
        self.assertEqual(result.status_code, 302)
        roles = CommunityRole.objects.filter(person=self.person).order_by("start")
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0].config, self.config1)
        self.assertEqual(roles[0].start, date(2022, 9, 1))
        self.assertEqual(roles[0].end, None)
        self.assertEqual(roles[1].config, self.config2)
        self.assertEqual(roles[1].start, date.today())
        self.assertEqual(roles[1].end, None)
