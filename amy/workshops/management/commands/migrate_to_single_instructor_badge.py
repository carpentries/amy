from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from workshops.models import Award, Badge, Person


class Command(BaseCommand):
    OLD_INSTRUCTOR_BADGE_NAMES = (
        "swc-instructor",
        "dc-instructor",
        "lc-instructor",
    )
    NEW_INSTRUCTOR_BADGE_NAME = "instructor"

    def __init__(self) -> None:
        super().__init__()
        self.instructor_badge = Badge.objects.get(name=self.NEW_INSTRUCTOR_BADGE_NAME)

    def find_instructors(self) -> QuerySet[Person]:
        return (
            Person.objects.filter(
                award__badge__name__in=self.OLD_INSTRUCTOR_BADGE_NAMES,
            )
            .exclude(award__badge__name=self.NEW_INSTRUCTOR_BADGE_NAME)
            .distinct()
        )

    def earliest_award(self, person: Person) -> Award:
        return (
            person.award_set.filter(  # type: ignore
                badge__name__in=self.OLD_INSTRUCTOR_BADGE_NAMES,
            )
            .order_by("awarded")
            .first()
        )

    def remove_awards_for_old_instructor_badges(self) -> None:
        Award.objects.filter(
            badge__name__in=self.OLD_INSTRUCTOR_BADGE_NAMES,
        ).exclude(badge__name=self.NEW_INSTRUCTOR_BADGE_NAME).delete()

    def create_instructor_award(self, person: Person) -> Award:
        earliest_award = self.earliest_award(person)
        return Award(
            person=person,
            badge=self.instructor_badge,
            awarded=earliest_award.awarded,
            event=earliest_award.event,
            awarded_by=earliest_award.awarded_by,
        )

    def log(self, no_output: bool, msg: str) -> None:
        if not no_output:
            self.stdout.write(msg)

    def handle(self, *args, **kwargs):
        no_output = kwargs.get("no_output", False)

        self.log(no_output, "Starting migration to a single instructor badge...")

        instructors = self.find_instructors()
        self.log(
            no_output,
            f"Found {len(instructors)} instructors with at least one SWC/DC/LC" " instructor badge.",
        )

        new_awards = [self.create_instructor_award(instructor) for instructor in instructors]
        self.log(no_output, f"Bulk-creating {len(new_awards)} new Instructor awards...")

        Award.objects.bulk_create(new_awards)
        self.log(no_output, "Done.")

        self.log(no_output, "Removing old instructor awards...")
        self.remove_awards_for_old_instructor_badges()
        self.log(no_output, "Done.")
