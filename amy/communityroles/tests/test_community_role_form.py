from datetime import date, timedelta

from django.contrib.contenttypes.models import ContentType

from communityroles.forms import CommunityRoleForm
from communityroles.models import CommunityRoleConfig
from fiscal.models import Membership
from workshops.models import Award, Badge, Lesson
from workshops.tests.base import TestBase


class TestCommunityRoleForm(TestBase):
    def setUp(self):
        super().setUp()

        test_badge = Badge.objects.create(name="test badge")
        self.award = Award.objects.create(person=self.hermione, badge=test_badge)
        self.membership = Membership.objects.create(
            variant="partner",
            registration_code="test-beta-code-test",
            agreement_start=date.today(),
            agreement_end=date.today() + timedelta(days=365),
            contribution_type="financial",
            workshops_without_admin_fee_per_agreement=10,
            public_instructor_training_seats=25,
            additional_public_instructor_training_seats=3,
        )

    def test_clean_success(self):
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=ContentType.objects.get_for_model(Lesson),
            generic_relation_multiple_items=True,
        )
        data = {
            "config": test_config.pk,
            "person": self.hermione.pk,
            "award": self.award.pk,
            "start": "2021-11-14",
            "end": "2022-11-14",
            "inactivation": None,
            "membership": self.membership.pk,
            "url": "https://example.org",
            "generic_relation_m2m": [1, 2, 3],
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})

    def test_award_required(self):
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=None,
            generic_relation_multiple_items=False,
        )
        data = {
            "config": test_config.pk,
            "person": self.hermione.pk,
            "award": None,  # should have an award
            "start": "2021-11-14",
            "end": "2022-11-14",
            "inactivation": None,
            "membership": self.membership.pk,
            "url": "https://example.org",
            "generic_relation_m2m": [],
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"award"})
        self.assertEqual(
            form.errors["award"], ["Award is required with community role Test"]
        )

    def test_specific_award_badge_required(self):
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=Badge.objects.get(name="swc-instructor"),
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=None,
            generic_relation_multiple_items=False,
        )
        data = {
            "config": test_config.pk,
            "person": self.hermione.pk,
            "award": self.award.pk,  # should have a specific badge
            "start": "2021-11-14",
            "end": "2022-11-14",
            "inactivation": None,
            "membership": self.membership.pk,
            "url": "https://example.org",
            "generic_relation_m2m": [],
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"award"})
        self.assertEqual(
            form.errors["award"],
            [
                "Award badge must be Software Carpentry Instructor "
                "for community role Test"
            ],
        )

    def test_membership_required(self):
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=None,
            generic_relation_multiple_items=False,
        )
        data = {
            "config": test_config.pk,
            "person": self.hermione.pk,
            "award": self.award.pk,
            "start": "2021-11-14",
            "end": "2022-11-14",
            "inactivation": None,
            "membership": None,  # should have a value
            "url": "https://example.org",
            "generic_relation_m2m": [],
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"membership"})
        self.assertEqual(
            form.errors["membership"],
            ["Membership is required with community role Test"],
        )

    def test_additional_url_supported(self):
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=False,
            generic_relation_content_type=None,
            generic_relation_multiple_items=False,
        )
        data = {
            "config": test_config.pk,
            "person": self.hermione.pk,
            "award": self.award.pk,
            "start": "2021-11-14",
            "end": "2022-11-14",
            "inactivation": None,
            "membership": self.membership.pk,
            "url": "https://example.org",  # should be empty
            "generic_relation_m2m": [],
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"url"})
        self.assertEqual(
            form.errors["url"],
            ["URL is not supported for community role Test"],
        )

    def test_multiple_items_for_generic_relation_supported(self):
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=ContentType.objects.get_for_model(Lesson),
            generic_relation_multiple_items=False,
        )
        data = {
            "config": test_config.pk,
            "person": self.hermione.pk,
            "award": self.award.pk,
            "start": "2021-11-14",
            "end": "2022-11-14",
            "inactivation": None,
            "membership": self.membership.pk,
            "url": "https://example.org",  # should be empty
            "generic_relation_m2m": [1, 2, 3],
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"generic_relation_m2m"})
        self.assertEqual(
            form.errors["generic_relation_m2m"],
            ["Multiple (>1) generic items are not supported for community role Test"],
        )

    def test_items_for_generic_relation_dont_exist(self):
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=ContentType.objects.get_for_model(Lesson),
            generic_relation_multiple_items=True,
        )
        data = {
            "config": test_config.pk,
            "person": self.hermione.pk,
            "award": self.award.pk,
            "start": "2021-11-14",
            "end": "2022-11-14",
            "inactivation": None,
            "membership": self.membership.pk,
            "url": "https://example.org",  # should be empty
            "generic_relation_m2m": [1234, 2222],
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"generic_relation_m2m"})
        self.assertEqual(
            form.errors["generic_relation_m2m"],
            ["Some generic relation objects of model Lesson don't exist: {1234, 2222}"],
        )
