from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from src.communityroles.models import CommunityRoleConfig
from src.workshops.models import Award, Badge, Person


class Command(BaseCommand):
    TRAINER_BADGE_NAME = "trainer"
    TRAINER_INACTIVE_BADGE_NAME = "trainer-inactive"
    TRAINER_COMMUNITY_ROLE_NAME = "trainer"

    def __init__(self) -> None:
        super().__init__()
        self.trainer_badge = Badge.objects.get(name=self.TRAINER_BADGE_NAME)
        self.trainer_inactive_badge = Badge.objects.get(name=self.TRAINER_INACTIVE_BADGE_NAME)
        self.community_role_config = CommunityRoleConfig.objects.get(name=self.TRAINER_COMMUNITY_ROLE_NAME)

    def find_people_with_trainer_community_role(self) -> QuerySet[Person]:
        return Person.objects.filter(communityrole__config=self.community_role_config)

    def find_trainer_inactive_awards(self) -> QuerySet[Award]:
        return Award.objects.filter(badge=self.trainer_inactive_badge)

    def log(self, no_output: bool, msg: str) -> None:
        if not no_output:
            self.stdout.write(msg)

    def handle(self, *args: Any, **kwargs: Any) -> None:
        no_output = kwargs.get("no_output", False)

        self.log(no_output, "Starting migration of inactive trainers to trainer badges...")

        people_with_trainer_community_role = self.find_people_with_trainer_community_role()
        self.log(
            no_output,
            f"Found {len(people_with_trainer_community_role)} people with Trainer community role.",
        )

        inactive_trainers = self.find_trainer_inactive_awards()
        self.log(
            no_output,
            f"Found {len(inactive_trainers)} people with 'Trainer - Inactive' badge.",
        )

        replace_badge = inactive_trainers.exclude(person__in=people_with_trainer_community_role)
        self.log(
            no_output,
            f"{len(replace_badge)} people will have their 'Trainer - Inactive' badge replaced with 'Trainer'.",
        )

        replace_badge.update(badge=self.trainer_badge)
        self.log(no_output, "Done.")
