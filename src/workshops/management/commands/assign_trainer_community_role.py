from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from src.communityroles.models import CommunityRole, CommunityRoleConfig
from src.workshops.models import Award, Badge


class Command(BaseCommand):
    TRAINER_BADGE_NAME = "trainer"
    TRAINER_COMMUNITY_ROLE_NAME = "trainer"

    def __init__(self) -> None:
        super().__init__()
        self.trainer_badge = Badge.objects.get(name=self.TRAINER_BADGE_NAME)
        self.community_role_config = CommunityRoleConfig.objects.get(name=self.TRAINER_COMMUNITY_ROLE_NAME)

    def find_trainer_awards(self) -> QuerySet[Award]:
        return Award.objects.filter(badge=self.trainer_badge)

    def exclude_trainer_community_roles(self, qs: QuerySet[Award]) -> QuerySet[Award]:
        return qs.exclude(person__communityrole__config=self.community_role_config)

    def create_trainer_community_role(self, award: Award) -> CommunityRole:
        return CommunityRole(
            config=self.community_role_config,
            person=award.person,
            award=award,
            start=award.awarded,
            end=None,
            inactivation=None,
        )

    def log(self, no_output: bool, msg: str) -> None:
        if not no_output:
            self.stdout.write(msg)

    def handle(self, *args, **kwargs):
        no_output = kwargs.get("no_output", False)

        self.log(no_output, "Starting migration to a trainer community role...")

        trainer_awards = self.exclude_trainer_community_roles(self.find_trainer_awards())
        self.log(no_output, f"Found {len(trainer_awards)} trainers with a Trainer badge.")

        new_community_roles = [self.create_trainer_community_role(trainer_award) for trainer_award in trainer_awards]
        self.log(
            no_output,
            f"Bulk-creating {len(new_community_roles)} new Trainer community roles...",
        )

        CommunityRole.objects.bulk_create(new_community_roles)
        self.log(no_output, "Done.")
