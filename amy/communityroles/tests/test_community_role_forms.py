from datetime import date, timedelta

from django.contrib.contenttypes.models import ContentType

from communityroles.forms import CommunityRoleForm, CommunityRoleUpdateForm
from communityroles.models import CommunityRole, CommunityRoleConfig
from fiscal.models import Membership
from workshops.models import Award, Badge, Lesson, Person
from workshops.tests.base import TestBase


class TestCommunityRoleForm(TestBase):
    def setUp(self):
        super().setUp()

        self.test_badge = Badge.objects.create(name="test badge")
        self.award = Award.objects.create(person=self.hermione, badge=self.test_badge)
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
        ct = ContentType.objects.get_for_model(Lesson)
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=ct,
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
            "generic_relation_content_type": ct.pk,
            "generic_relation_pk": self.git.pk,  # Lesson instance
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})

    def test_empty_payload(self):
        data = {}

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"config", "person"})
        self.assertEqual(form.errors["config"], ["This field is required."])
        self.assertEqual(form.errors["person"], ["This field is required."])

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
            "generic_relation_content_type": None,
            "generic_relation_pk": None,
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"award"})
        self.assertEqual(
            form.errors["award"], ["Award is required with community role Test"]
        )

    def test_award_same_person_required(self):
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=None,
        )
        award = Award.objects.create(person=self.harry, badge=self.test_badge)
        data = {
            "config": test_config.pk,
            "person": self.hermione.pk,
            "award": award.pk,
            "start": "2021-11-14",
            "end": "2022-11-14",
            "inactivation": None,
            "membership": self.membership.pk,
            "url": "https://example.org",
            "generic_relation_content_type": None,
            "generic_relation_pk": None,
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"award"})
        self.assertEqual(
            form.errors["award"], [f"Award should belong to {self.hermione}"]
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
            "generic_relation_content_type": None,
            "generic_relation_pk": None,
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
            "generic_relation_content_type": None,
            "generic_relation_pk": None,
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

    def test_start_date_gt_end_date_is_invalid(self):
        """Tests error raised if end < start"""
        # Arrange
        data = {
            "start": date(2021, 11, 14),
            "end": date(2021, 11, 13),  # lt start
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertIn("end", form.errors.keys())
        self.assertEqual(
            form.errors["end"],
            ["Must not be earlier than start date."],
        )

    def test_start_end_dates_valid(self):
        """Tests valid start date <= end date"""
        # Arrange
        params = [
            (date(2021, 11, 14), date(2021, 11, 14)),
            (date(2021, 11, 14), date(2021, 11, 15)),
        ]

        for p1, p2 in params:
            data = {
                "start": p1,
                "end": p2,
            }

            # Act
            form = CommunityRoleForm(data)
            form.is_valid()

            # Assert
            with self.subTest():
                self.assertEqual(form.cleaned_data.get("end"), p2)
                self.assertNotIn("end", form.errors.keys())

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
            "generic_relation_content_type": None,
            "generic_relation_pk": None,
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

    def test_generic_relation_object_doesnt_exist(self):
        # Arrange
        ct = ContentType.objects.get_for_model(Lesson)
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
            generic_relation_content_type=ct,
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
            "generic_relation_content_type": ct.pk,
            "generic_relation_pk": None,
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"generic_relation_pk"})
        self.assertEqual(
            form.errors["generic_relation_pk"],
            ["Generic relation object of model Lesson doesn't exist"],
        )


class TestCommunityRoleUpdateForm(TestBase):
    def test_fields(self) -> None:
        # Arrange
        config = CommunityRoleConfig(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
        )
        # Act
        form = CommunityRoleUpdateForm(community_role_config=config)
        # Assert
        self.assertEqual(
            form.fields.keys(),
            {
                "config",
                "person",
                "award",
                "start",
                "end",
                "inactivation",
                "membership",
                "url",
                "generic_relation_content_type",
                "generic_relation_pk",
                "custom_keys",
            },
        )

    def test_config_field_disabled(self) -> None:
        # Arrange
        config = CommunityRoleConfig(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
        )
        # Act
        form = CommunityRoleUpdateForm(community_role_config=config)
        # Assert
        self.assertTrue(form.fields["config"].disabled)

    def test_custom_labels_applied(self) -> None:
        # Arrange
        labels = ["Label 1", "Another label"]
        config = CommunityRoleConfig(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            additional_url=True,
            custom_key_labels=labels,
        )
        # Act
        form = CommunityRoleUpdateForm(community_role_config=config)
        # Assert
        self.assertEqual(form.fields["custom_keys"].labels, labels)

    def test_empty_payload(self) -> None:
        # Arrange
        data = {}
        person = Person.objects.create(personal="Test", family="Test")
        config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=False,
            award_badge_limit=None,
            link_to_membership=False,
            additional_url=True,
            custom_key_labels=["Label 1", "Another label"],
        )
        role = CommunityRole.objects.create(person=person, config=config)

        # Act
        form = CommunityRoleUpdateForm(
            data, instance=role, community_role_config=config
        )

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"person"})
        self.assertEqual(form.errors["person"], ["This field is required."])

    def test_clean_success(self) -> None:
        # Arrange
        person = Person.objects.create(personal="Test", family="Test")
        config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=False,
            award_badge_limit=None,
            link_to_membership=False,
            additional_url=True,
            custom_key_labels=["Label 1", "Another label"],
        )
        role = CommunityRole.objects.create(person=person, config=config)
        data = {
            "config": config.pk,
            "person": person.pk,
            "award": "",
            "start": "",
            "end": "",
            "inactivation": None,
            "membership": "",
            "url": "",
            "generic_relation_content_type": "",
            "generic_relation_pk": "",
        }

        # Act
        form = CommunityRoleUpdateForm(
            data, instance=role, community_role_config=config
        )

        # Assert
        self.assertTrue(form.is_valid(), form.errors)

    def test_custom_keys_field(self) -> None:
        # Arrange
        labels = ["Label 1", "Another label"]
        person = Person.objects.create(personal="Test", family="Test")
        config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=False,
            award_badge_limit=None,
            link_to_membership=False,
            additional_url=True,
            custom_key_labels=labels,
        )
        role = CommunityRole.objects.create(person=person, config=config)
        data = {
            "config": config.pk,
            "person": person.pk,
            "award": "",
            "start": "",
            "end": "",
            "inactivation": None,
            "membership": "",
            "url": "",
            "generic_relation_content_type": "",
            "generic_relation_pk": "",
            "custom_keys": ["", "another value"],
        }
        form = CommunityRoleUpdateForm(
            data, instance=role, community_role_config=config
        )

        # Act
        form.save()
        role.refresh_from_db()

        # Assert
        self.assertEqual(
            role.custom_keys,
            [["Label 1", ""], ["Another label", "another value"]],
        )
