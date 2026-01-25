from datetime import date, timedelta
from typing import Any

from django.contrib.contenttypes.models import ContentType

from src.communityroles.forms import CommunityRoleForm, CommunityRoleUpdateForm
from src.communityroles.models import (
    CommunityRole,
    CommunityRoleConfig,
    CommunityRoleInactivation,
)
from src.workshops.models import Award, Badge, Lesson, Membership, Person
from src.workshops.tests.base import TestBase


class TestCommunityRoleForm(TestBase):
    def setUp(self) -> None:
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

    def test_clean_success(self) -> None:
        # Arrange
        ct = ContentType.objects.get_for_model(Lesson)
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            link_to_partnership=False,
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

    def test_empty_payload(self) -> None:
        data: dict[str, Any] = {}

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"config", "person", "start"})
        self.assertEqual(form.errors["config"], ["This field is required."])
        self.assertEqual(form.errors["person"], ["This field is required."])
        self.assertEqual(form.errors["start"], ["This field is required."])

    def test_award_required(self) -> None:
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            link_to_partnership=False,
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
        self.assertEqual(form.errors["award"], ["Award is required with community role Test"])

    def test_award_same_person_required(self) -> None:
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            link_to_partnership=False,
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
        self.assertEqual(form.errors["award"], [f"Award should belong to {self.hermione}"])

    def test_specific_award_badge_required(self) -> None:
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=Badge.objects.get(name="swc-instructor"),
            link_to_membership=True,
            link_to_partnership=False,
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
            ["Award badge must be Software Carpentry Instructor for community role Test"],
        )

    def test_membership_required(self) -> None:
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            link_to_partnership=False,
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

    def test_start_date_gt_end_date_is_invalid(self) -> None:
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

    def test_start_end_dates_valid(self) -> None:
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

    def test_additional_url_required(self) -> None:
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            link_to_partnership=False,
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
            "membership": self.membership.pk,
            "url": "",  # shouldn't be empty
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
            ["URL is required for community role Test"],
        )

    def test_additional_url_not_required(self) -> None:
        # Arrange
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            link_to_partnership=False,
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
            "url": "",  # it's okay
            "generic_relation_content_type": None,
            "generic_relation_pk": None,
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertTrue(form.is_valid())  # errors not expected
        self.assertEqual(form.errors.keys(), set())

    def test_generic_relation_object_doesnt_exist(self) -> None:
        # Arrange
        ct = ContentType.objects.get_for_model(Lesson)
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            link_to_partnership=False,
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
            "generic_relation_pk": 102390128371902,
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

    def test_end_date_required_when_inactivation_selected(self) -> None:
        """Should not validate if the inactivation reason is provided and end date
        is missing."""
        # Arrange
        ct = ContentType.objects.get_for_model(Lesson)
        inactivation = CommunityRoleInactivation.objects.create(name="End of term")
        test_config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            link_to_partnership=False,
            additional_url=True,
            generic_relation_content_type=ct,
        )
        data = {
            "config": test_config.pk,
            "person": self.hermione.pk,
            "award": self.award.pk,
            "start": "2021-11-14",
            "end": None,
            "inactivation": inactivation.pk,
            "membership": self.membership.pk,
            "url": "https://example.org",
            "generic_relation_content_type": ct.pk,
            "generic_relation_pk": self.git.pk,  # Lesson instance
        }

        # Act
        form = CommunityRoleForm(data)

        # Assert
        self.assertFalse(form.is_valid())
        self.assertEqual(form.errors.keys(), {"end"})
        self.assertEqual(form.errors["end"], ["Required when Reason for inactivation selected."])

    def test_find_concurrent_roles(self) -> None:
        # Arrange
        config1 = CommunityRoleConfig.objects.create(
            name="test1",
            display_name="Test1",
            link_to_award=False,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        config2 = CommunityRoleConfig.objects.create(
            name="test2",
            display_name="Test2",
            link_to_award=False,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=True,
        )
        role1 = CommunityRole.objects.create(
            person=self.hermione,
            config=config1,
            start=date(2022, 9, 29),
            end=date(2023, 9, 29),
        )
        role2 = CommunityRole.objects.create(
            person=self.hermione,
            config=config2,
            start=date(2022, 9, 29),
            end=date(2023, 9, 29),
            url="https://example.org/",
        )
        # Act
        roles1 = CommunityRoleForm.find_concurrent_roles(config1, self.hermione, date(2022, 1, 1), date(2022, 1, 31))
        roles2 = CommunityRoleForm.find_concurrent_roles(config1, self.hermione, date(2022, 10, 1), date(2022, 10, 31))
        roles3 = CommunityRoleForm.find_concurrent_roles(
            config2, self.hermione, date(2022, 10, 1), date(2022, 10, 31), url=None
        )
        roles4 = CommunityRoleForm.find_concurrent_roles(
            config2, self.hermione, date(2022, 10, 1), date(2022, 10, 31), url=""
        )
        roles5 = CommunityRoleForm.find_concurrent_roles(
            config2,
            self.hermione,
            date(2022, 10, 1),
            date(2022, 10, 31),
            url="https://example.org/",
        )
        # Assert
        self.assertEqual(list(roles1), [])  # type: ignore
        self.assertEqual(list(roles2), [role1])  # type: ignore
        self.assertEqual(list(roles3), [])  # type: ignore
        self.assertEqual(list(roles4), [])  # type: ignore
        self.assertEqual(list(roles5), [role2])  # type: ignore

    def test_concurrent_community_roles_disallowed__validation_errors(self) -> None:
        """"""
        # Arrange
        config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=False,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        # When the validation failures should occur - failure feed data.
        failure_data = [
            # community role start, end, form start, form end
            (date(2022, 9, 17), date(2023, 9, 16), "2022-10-01", "2022-10-31"),
            (date(2022, 9, 17), date(2023, 9, 16), "2022-01-01", "2022-10-31"),
            (date(2022, 9, 17), date(2023, 9, 16), "2023-01-01", "2023-10-31"),
            (date(2022, 9, 17), None, "2022-10-01", "2022-10-31"),
            (date(2022, 9, 17), None, "2022-01-01", "2022-10-31"),
            (date(2022, 9, 17), None, "2022-10-01", None),
            (date(2022, 9, 17), None, "2022-01-01", None),
            (None, None, "2022-01-01", None),
        ]
        for role_start, role_end, form_start, form_end in failure_data:
            with self.subTest(
                role_start=role_start,
                role_end=role_end,
                form_start=form_start,
                form_end=form_end,
            ):
                # clear community roles if the test suite doesn't
                CommunityRole.objects.filter(config=config, person=self.hermione).delete()

                community_role = CommunityRole.objects.create(
                    config=config,
                    person=self.hermione,
                    start=role_start,
                    end=role_end,
                )
                form_data = {
                    "config": config.pk,
                    "person": self.hermione.pk,
                    "award": self.award.pk,
                    "start": form_start,
                    "end": form_end,
                    "inactivation": None,
                    "membership": None,
                    "url": "",
                    "generic_relation_content_type": None,
                    "generic_relation_pk": None,
                }

                # Act
                form = CommunityRoleForm(form_data)
                # Assert
                self.assertFalse(form.is_valid())
                self.assertEqual(form.errors.keys(), {"person"})
                self.assertEqual(
                    form.errors["person"],
                    [f"Person {self.hermione} has concurrent community roles: {[community_role]}."],
                )

    def test_concurrent_community_roles_disallowed__validation_succeeds(self) -> None:
        """"""
        # Arrange
        config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=False,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        # When the validation failures should NOT occur - pass feed data.
        pass_data = [
            # community role start, end, form start, form end
            (date(2022, 9, 17), date(2023, 9, 16), "2023-09-16", "2023-09-30"),
            (date(2022, 9, 17), date(2023, 9, 16), "2022-01-01", "2022-09-17"),
            (None, date(2022, 9, 17), "2022-09-17", None),
        ]
        for role_start, role_end, form_start, form_end in pass_data:
            with self.subTest(
                role_start=role_start,
                role_end=role_end,
                form_start=form_start,
                form_end=form_end,
            ):
                # clear community roles if the test suite doesn't
                CommunityRole.objects.filter(config=config, person=self.hermione).delete()

                CommunityRole.objects.create(
                    config=config,
                    person=self.hermione,
                    start=role_start,
                    end=role_end,
                )
                form_data = {
                    "config": config.pk,
                    "person": self.hermione.pk,
                    "award": self.award.pk,
                    "start": form_start,
                    "end": form_end,
                    "inactivation": None,
                    "membership": None,
                    "url": "",
                    "generic_relation_content_type": None,
                    "generic_relation_pk": None,
                }

                # Act
                form = CommunityRoleForm(form_data)
                # Assert
                self.assertTrue(form.is_valid())
                self.assertEqual(form.errors.keys(), set())


class TestCommunityRoleUpdateForm(TestBase):
    def test_fields(self) -> None:
        # Arrange
        config = CommunityRoleConfig(
            name="test",
            display_name="Test",
            link_to_award=True,
            award_badge_limit=None,
            link_to_membership=True,
            link_to_partnership=False,
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
                "partnership",
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
            link_to_partnership=False,
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
            link_to_partnership=False,
            additional_url=True,
            custom_key_labels=labels,
        )
        # Act
        form = CommunityRoleUpdateForm(community_role_config=config)
        # Assert
        self.assertEqual(form.fields["custom_keys"].labels, labels)  # type: ignore

    def test_empty_payload(self) -> None:
        # Arrange
        data: dict[str, Any] = {}
        person = Person.objects.create(personal="Test", family="Test")
        config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=False,
            award_badge_limit=None,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=True,
            custom_key_labels=["Label 1", "Another label"],
        )
        role = CommunityRole.objects.create(person=person, config=config)

        # Act
        form = CommunityRoleUpdateForm(data, instance=role, community_role_config=config)

        # Assert
        self.assertFalse(form.is_valid())  # errors expected
        self.assertEqual(form.errors.keys(), {"person", "start"})
        self.assertEqual(form.errors["person"], ["This field is required."])
        self.assertEqual(form.errors["start"], ["This field is required."])

    def test_clean_success(self) -> None:
        # Arrange
        person = Person.objects.create(personal="Test", family="Test")
        config = CommunityRoleConfig.objects.create(
            name="test",
            display_name="Test",
            link_to_award=False,
            award_badge_limit=None,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=True,
            custom_key_labels=["Label 1", "Another label"],
        )
        role = CommunityRole.objects.create(person=person, config=config)
        data = {
            "config": config.pk,
            "person": person.pk,
            "award": "",
            "start": "2022-09-17",
            "end": "",
            "inactivation": None,
            "membership": "",
            "url": "https://example.org/",
            "generic_relation_content_type": "",
            "generic_relation_pk": "",
        }

        # Act
        form = CommunityRoleUpdateForm(data, instance=role, community_role_config=config)

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
            link_to_partnership=False,
            additional_url=True,
            custom_key_labels=labels,
        )
        role = CommunityRole.objects.create(person=person, config=config)
        data = {
            "config": config.pk,
            "person": person.pk,
            "award": "",
            "start": "2022-09-17",
            "end": "",
            "inactivation": None,
            "membership": "",
            "url": "https://example.org/",
            "generic_relation_content_type": "",
            "generic_relation_pk": "",
            "custom_keys": ["", "another value"],
        }
        form = CommunityRoleUpdateForm(data, instance=role, community_role_config=config)

        # Act
        form.save()
        role.refresh_from_db()

        # Assert
        self.assertEqual(
            role.custom_keys,
            [["Label 1", ""], ["Another label", "another value"]],
        )
