"""This file contains tests for individual management commands

These commands are run via `./manage.py command`."""

from datetime import date

from django.core.management.base import BaseCommand
from django.test import TestCase

from src.communityroles.models import CommunityRole, CommunityRoleConfig
from src.workshops.management.commands.assign_instructor_community_role import (
    Command as AssignInstructorCommunityRole,
)
from src.workshops.management.commands.assign_trainer_community_role import (
    Command as AssignTrainerCommunityRole,
)
from src.workshops.management.commands.create_superuser import Command as CreateSuperuser
from src.workshops.management.commands.migrate_inactive_trainers_to_trainer_badges import (
    Command as MigrateInactiveTrainersToTrainerBadges,
)
from src.workshops.management.commands.migrate_to_single_instructor_badge import (
    Command as MigrateToSingleInstructorBadge,
)
from src.workshops.models import Award, Badge, Person


class TestMigrateToSingleInstructorBadge(TestCase):
    def setUp(self) -> None:
        self.swc_instructor = Badge.objects.get(name="swc-instructor")
        self.dc_instructor = Badge.objects.get(name="dc-instructor")
        self.lc_instructor = Badge.objects.get(name="lc-instructor")
        self.instructor_badge = Badge.objects.create(name="instructor", title="Instructor")
        self.command = MigrateToSingleInstructorBadge()

    def test___init__(self) -> None:
        # Act
        # Assert
        self.assertEqual(self.command.instructor_badge, Badge.objects.get(name="instructor"))

    def test_find_instructors(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        Award.objects.create(person=person1, badge=self.swc_instructor)
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        Award.objects.create(person=person2, badge=self.swc_instructor)
        Award.objects.create(person=person2, badge=self.dc_instructor)
        person3 = Person.objects.create(username="test3", personal="Test3", family="User", email="test3@example.org")
        Award.objects.create(person=person3, badge=self.swc_instructor)
        Award.objects.create(person=person3, badge=self.dc_instructor)
        Award.objects.create(person=person3, badge=self.lc_instructor)
        Award.objects.create(person=person3, badge=self.instructor_badge)

        # Act
        instructors = self.command.find_instructors()

        # Assert
        self.assertEqual([person1, person2], list(instructors))

    def test_earliest_award(self) -> None:
        # Arrange
        person = Person.objects.create(username="test", personal="Test", family="User", email="test@example.org")
        Award.objects.create(person=person, badge=self.swc_instructor, awarded=date(2022, 1, 1))
        Award.objects.create(person=person, badge=self.dc_instructor, awarded=date(2021, 1, 1))
        award = Award.objects.create(person=person, badge=self.lc_instructor, awarded=date(2020, 1, 1))
        Award.objects.create(person=person, badge=self.instructor_badge, awarded=date(1999, 1, 1))

        # Act
        earliest_award = self.command.earliest_award(person)

        # Assert
        self.assertEqual(earliest_award, award)

    def test_remove_awards_for_old_instructor_badges(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        Award.objects.create(person=person1, badge=self.swc_instructor)
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        Award.objects.create(person=person2, badge=self.swc_instructor)
        Award.objects.create(person=person2, badge=self.dc_instructor)
        person3 = Person.objects.create(username="test3", personal="Test3", family="User", email="test3@example.org")
        Award.objects.create(person=person3, badge=self.swc_instructor)
        Award.objects.create(person=person3, badge=self.dc_instructor)
        Award.objects.create(person=person3, badge=self.lc_instructor)
        instructor_award = Award.objects.create(person=person3, badge=self.instructor_badge)

        # Act
        self.command.remove_awards_for_old_instructor_badges()

        # Assert
        self.assertEqual(list(Award.objects.filter(person=person1)), [])
        self.assertEqual(list(Award.objects.filter(person=person2)), [])
        self.assertEqual(list(Award.objects.filter(person=person3)), [instructor_award])

    def test_create_instructor_award(self) -> None:
        # Arrange
        person = Person.objects.create(username="test", personal="Test", family="User", email="test@example.org")
        Award.objects.create(person=person, badge=self.swc_instructor, awarded=date(2022, 1, 1))
        Award.objects.create(person=person, badge=self.dc_instructor, awarded=date(2021, 1, 1))
        Award.objects.create(person=person, badge=self.lc_instructor, awarded=date(2020, 1, 1))

        # Act
        instructor_award = self.command.create_instructor_award(person)

        # Assert
        self.assertEqual(instructor_award.person, person)
        self.assertEqual(instructor_award.badge, self.instructor_badge)
        self.assertEqual(instructor_award.awarded, date(2020, 1, 1))
        self.assertEqual(instructor_award.event, None)
        self.assertEqual(instructor_award.awarded_by, None)

    def test_handle(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        Award.objects.create(person=person1, badge=self.swc_instructor, awarded=date(2022, 1, 1))
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        Award.objects.create(person=person2, badge=self.swc_instructor, awarded=date(2021, 1, 1))
        Award.objects.create(person=person2, badge=self.dc_instructor, awarded=date(2022, 1, 1))
        person3 = Person.objects.create(username="test3", personal="Test3", family="User", email="test3@example.org")
        Award.objects.create(person=person3, badge=self.swc_instructor, awarded=date(2020, 1, 1))
        Award.objects.create(person=person3, badge=self.dc_instructor, awarded=date(2021, 1, 1))
        Award.objects.create(person=person3, badge=self.lc_instructor, awarded=date(2022, 1, 1))
        expected = [
            Award(
                person=person3,
                badge=self.instructor_badge,
                awarded=date(2020, 1, 1),
                event=None,
                awarded_by=None,
            ),
            Award(
                person=person2,
                badge=self.instructor_badge,
                awarded=date(2021, 1, 1),
                event=None,
                awarded_by=None,
            ),
            Award(
                person=person1,
                badge=self.instructor_badge,
                awarded=date(2022, 1, 1),
                event=None,
                awarded_by=None,
            ),
        ]

        # Act
        self.command.handle(no_output=True)

        # Assert
        for db, exp in zip(list(Award.objects.order_by("-pk")), expected, strict=False):
            # Can't compare db == exp, since exp isn't from database and
            # doesn't contain a PK.
            self.assertEqual(db.person, exp.person)
            self.assertEqual(db.badge, exp.badge)
            self.assertEqual(db.awarded, exp.awarded)
            self.assertEqual(db.event, exp.event)
            self.assertEqual(db.awarded_by, exp.awarded_by)


class TestAssignInstructorCommunityRole(TestCase):
    def setUp(self) -> None:
        self.swc_instructor = Badge.objects.get(name="swc-instructor")
        self.dc_instructor = Badge.objects.get(name="dc-instructor")
        self.lc_instructor = Badge.objects.get(name="lc-instructor")
        self.instructor_badge = Badge.objects.create(name="instructor", title="Instructor")
        self.instructor_community_role_config = CommunityRoleConfig.objects.create(
            name="instructor",
            link_to_award=True,
            award_badge_limit=self.instructor_badge,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        self.command = AssignInstructorCommunityRole()

    def test___init__(self) -> None:
        # Act
        # Assert
        self.assertEqual(self.command.instructor_badge, Badge.objects.get(name="instructor"))
        self.assertEqual(
            self.command.community_role_config,
            self.instructor_community_role_config,
        )

    def test_find_instructor_awards(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        Award.objects.create(person=person1, badge=self.swc_instructor)
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        Award.objects.create(person=person2, badge=self.instructor_badge)
        person3 = Person.objects.create(username="test3", personal="Test3", family="User", email="test3@example.org")
        Award.objects.create(person=person3, badge=self.dc_instructor)
        Award.objects.create(person=person3, badge=self.instructor_badge)

        # Act
        instructor_awards = self.command.find_instructor_awards()

        # Assert
        self.assertEqual(len(instructor_awards), 2)
        self.assertEqual(instructor_awards[0].person, person2)
        self.assertEqual(instructor_awards[1].person, person3)

    def test_exclude_instructor_community_roles(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        award1 = Award.objects.create(person=person1, badge=self.instructor_badge)
        CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=person1,
            award=award1,
            start=date.today(),
            end=None,
        )
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        Award.objects.create(person=person2, badge=self.instructor_badge)

        # Act
        instructor_awards = self.command.exclude_instructor_community_roles(self.command.find_instructor_awards())

        # Assert
        self.assertEqual(len(instructor_awards), 1)
        self.assertEqual(instructor_awards[0].person, person2)

    def test_create_instructor_community_role(self) -> None:
        # Arrange
        person = Person.objects.create(username="test", personal="Test", family="User", email="test@example.org")
        award = Award.objects.create(person=person, badge=self.instructor_badge, awarded=date(2022, 1, 1))

        # Act
        instructor_community_role = self.command.create_instructor_community_role(award)

        # Assert
        self.assertEqual(instructor_community_role.config, self.instructor_community_role_config)
        self.assertEqual(instructor_community_role.person, person)
        self.assertEqual(instructor_community_role.award, award)
        self.assertEqual(instructor_community_role.start, award.awarded)
        self.assertEqual(instructor_community_role.end, None)

    def test_handle(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        award1 = Award.objects.create(person=person1, badge=self.instructor_badge, awarded=date(2022, 1, 1))
        CommunityRole.objects.create(
            config=self.instructor_community_role_config,
            person=person1,
            award=award1,
            start=date.today(),
            end=None,
        )
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        award2 = Award.objects.create(person=person2, badge=self.instructor_badge, awarded=date(2021, 1, 1))
        Award.objects.create(person=person2, badge=self.dc_instructor, awarded=date(2022, 1, 1))
        person3 = Person.objects.create(username="test3", personal="Test3", family="User", email="test3@example.org")
        award3 = Award.objects.create(person=person3, badge=self.instructor_badge, awarded=date(2020, 1, 1))
        expected = [
            CommunityRole(
                config=self.instructor_community_role_config,
                person=person2,
                award=award2,
                start=date(2021, 1, 1),
                end=None,
            ),
            CommunityRole(
                config=self.instructor_community_role_config,
                person=person3,
                award=award3,
                start=date(2020, 1, 1),
                end=None,
            ),
        ]

        # Act
        self.command.handle(no_output=True)

        # Assert
        for db, exp in zip(list(CommunityRole.objects.order_by("-pk")[:2]), expected, strict=False):
            # Can't compare db == exp, since exp isn't from database and
            # doesn't contain a PK.
            self.assertEqual(db.config, exp.config)
            self.assertEqual(db.person, exp.person)
            self.assertEqual(db.award, exp.award)
            self.assertEqual(db.start, exp.award.awarded)  # type: ignore
            self.assertEqual(db.end, None)


class TestAssignTrainerCommunityRole(TestCase):
    def setUp(self) -> None:
        self.trainer_badge = Badge.objects.get(name="trainer")
        self.trainer_community_role_config = CommunityRoleConfig.objects.create(
            name="trainer",
            link_to_award=True,
            award_badge_limit=self.trainer_badge,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        self.command = AssignTrainerCommunityRole()

    def test___init__(self) -> None:
        # Assert
        self.assertEqual(self.command.trainer_badge, self.trainer_badge)
        self.assertEqual(
            self.command.community_role_config,
            self.trainer_community_role_config,
        )

    def test_find_trainer_awards(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        Award.objects.create(person=person1, badge=self.trainer_badge)
        Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")

        # Act
        trainer_awards = self.command.find_trainer_awards()

        # Assert
        self.assertEqual(len(trainer_awards), 1)
        self.assertEqual(trainer_awards[0].person, person1)

    def test_exclude_trainer_community_roles(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        award1 = Award.objects.create(person=person1, badge=self.trainer_badge)
        CommunityRole.objects.create(
            config=self.trainer_community_role_config,
            person=person1,
            award=award1,
            start=date.today(),
            end=None,
        )
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        Award.objects.create(person=person2, badge=self.trainer_badge)

        # Act
        trainer_awards = self.command.exclude_trainer_community_roles(self.command.find_trainer_awards())

        # Assert
        self.assertEqual(len(trainer_awards), 1)
        self.assertEqual(trainer_awards[0].person, person2)

    def test_create_trainer_community_role(self) -> None:
        # Arrange
        person = Person.objects.create(username="test", personal="Test", family="User", email="test@example.org")
        award = Award.objects.create(person=person, badge=self.trainer_badge, awarded=date(2022, 1, 1))

        # Act
        trainer_community_role = self.command.create_trainer_community_role(award)

        # Assert
        self.assertEqual(trainer_community_role.config, self.trainer_community_role_config)
        self.assertEqual(trainer_community_role.person, person)
        self.assertEqual(trainer_community_role.award, award)
        self.assertEqual(trainer_community_role.start, award.awarded)
        self.assertEqual(trainer_community_role.end, None)

    def test_handle(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        award1 = Award.objects.create(person=person1, badge=self.trainer_badge, awarded=date(2022, 1, 1))
        CommunityRole.objects.create(
            config=self.trainer_community_role_config,
            person=person1,
            award=award1,
            start=date.today(),
            end=None,
        )
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        award2 = Award.objects.create(person=person2, badge=self.trainer_badge, awarded=date(2021, 1, 1))
        expected = CommunityRole(
            config=self.trainer_community_role_config,
            person=person2,
            award=award2,
            start=date(2021, 1, 1),
            end=None,
        )

        # Act
        self.command.handle(no_output=True)

        # Assert
        self.assertEqual(CommunityRole.objects.count(), 2)  # only 1 created
        records = list(CommunityRole.objects.all())
        self.assertEqual(records[-1].config, expected.config)
        self.assertEqual(records[-1].person, expected.person)
        self.assertEqual(records[-1].award, expected.award)
        self.assertEqual(records[-1].start, expected.start)
        self.assertEqual(records[-1].end, None)


class TestMigrateInactiveTrainersToTrainerBadges(TestCase):
    def setUp(self) -> None:
        self.trainer_badge = Badge.objects.get(name="trainer")
        self.trainer_inactive_badge, _ = Badge.objects.get_or_create(name="trainer-inactive")
        self.trainer_community_role_config = CommunityRoleConfig.objects.create(
            name="trainer",
            link_to_award=True,
            award_badge_limit=self.trainer_badge,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )
        self.command = MigrateInactiveTrainersToTrainerBadges()

    def test__init__(self) -> None:
        # Assert
        self.assertEqual(self.command.trainer_badge, self.trainer_badge)
        self.assertEqual(self.command.trainer_inactive_badge, self.trainer_inactive_badge)
        self.assertEqual(
            self.command.community_role_config,
            self.trainer_community_role_config,
        )

    def test_find_people_with_trainer_community_role(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        award1 = Award.objects.create(person=person1, badge=self.trainer_badge)
        CommunityRole.objects.create(
            config=self.trainer_community_role_config,
            person=person1,
            award=award1,
            start=date.today(),
            end=None,
        )
        Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")

        # Act
        people_with_trainer_community_roles = self.command.find_people_with_trainer_community_role()

        # Assert
        self.assertEqual(list(people_with_trainer_community_roles), [person1])

    def test_find_trainer_inactive_awards(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        Award.objects.create(person=person1, badge=self.trainer_badge)
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        award2 = Award.objects.create(person=person2, badge=self.trainer_inactive_badge)

        # Act
        trainer_inactive_awards = self.command.find_trainer_inactive_awards()

        # Assert
        self.assertEqual(list(trainer_inactive_awards), [award2])

    def test_handle(self) -> None:
        # Arrange
        person1 = Person.objects.create(username="test1", personal="Test1", family="User", email="test1@example.org")
        award1 = Award.objects.create(person=person1, badge=self.trainer_badge, awarded=date(2022, 1, 1))
        CommunityRole.objects.create(
            config=self.trainer_community_role_config,
            person=person1,
            award=award1,
            start=date.today(),
            end=None,
        )
        person2 = Person.objects.create(username="test2", personal="Test2", family="User", email="test2@example.org")
        award2 = Award.objects.create(person=person2, badge=self.trainer_inactive_badge, awarded=date(2021, 1, 1))

        # Act
        self.command.handle(no_output=True)

        # Assert
        award1.refresh_from_db()
        award2.refresh_from_db()
        self.assertEqual(award2.badge, self.trainer_badge)  # Changed
        self.assertEqual(award2.awarded, date(2021, 1, 1))
        self.assertEqual(award1.badge, self.trainer_badge)  # Not changed


class TestCreateSuperuserCommand(TestCase):
    command: BaseCommand

    def setUp(self) -> None:
        self.command = CreateSuperuser()
        instructor_badge = Badge.objects.create(name="instructor", title="Instructor")
        CommunityRoleConfig.objects.create(
            name="instructor",
            link_to_award=True,
            award_badge_limit=instructor_badge,
            link_to_membership=False,
            link_to_partnership=False,
            additional_url=False,
        )

    def test_admin_created(self) -> None:
        """When `admin` account doesn't exist, it gets created."""
        # Act
        self.command.handle()

        # Assert
        Person.objects.get(username="admin")

    def test_admin_not_created(self) -> None:
        """When `admin` account exists, the command doesn't change it or create other
        superuser accounts."""
        # Arrange
        superuser = Person.objects.create_superuser(
            username="admin",
            personal="admin",
            family="admin",
            email="admin@example.org",
            password="admin",
        )
        superuser.is_active = False
        superuser.save()

        # Act
        self.command.handle()

        # Assert
        Person.objects.get(username="admin")
        self.assertEqual(Person.objects.filter(is_superuser=True).count(), 1)
        superuser.refresh_from_db()
        self.assertFalse(superuser.is_active)
