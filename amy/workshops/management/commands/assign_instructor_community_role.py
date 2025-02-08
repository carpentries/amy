from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from communityroles.models import CommunityRole, CommunityRoleConfig
from workshops.models import Award, Badge


class Command(BaseCommand):
    def __init__(self) -> None:
        super().__init__()
        self.instructor_badge = Badge.objects.get(name="instructor")
        self.community_role_config = CommunityRoleConfig.objects.get(name="instructor")

    def find_instructor_awards(self) -> QuerySet[Award]:
        return Award.objects.filter(badge=self.instructor_badge)

    def exclude_instructor_community_roles(self, qs: QuerySet[Award]) -> QuerySet[Award]:
        return qs.exclude(person__communityrole__config=self.community_role_config)

    def create_instructor_community_role(self, award: Award) -> CommunityRole:
        return CommunityRole(
            config=self.community_role_config,
            person=award.person,
            award=award,
            start=award.awarded,
            end=None,
        )

    def log(self, no_output: bool, msg: str) -> None:
        if not no_output:
            self.stdout.write(msg)

    def handle(self, *args, **kwargs):
        no_output = kwargs.get("no_output", False)

        self.log(no_output, "Starting migration to a single instructor badge...")

        instructor_awards = self.exclude_instructor_community_roles(self.find_instructor_awards())
        self.log(
            no_output,
            f"Found {len(instructor_awards)} instructors with the Instructor Badge and"
            " without Instructor Community Role.",
        )

        new_community_roles = [
            self.create_instructor_community_role(instructor_award) for instructor_award in instructor_awards
        ]
        self.log(
            no_output,
            f"Bulk-creating {len(new_community_roles)} new Instructor Community" " Roles...",
        )

        CommunityRole.objects.bulk_create(new_community_roles)
        self.log(no_output, "Done.")
