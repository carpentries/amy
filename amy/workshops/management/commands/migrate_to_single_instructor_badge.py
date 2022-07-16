from django.core.management.base import BaseCommand
from django.db.models import QuerySet

from workshops.models import Award, Badge, Person


class Command(BaseCommand):
    def __init__(self) -> None:
        super().__init__()
        self.instructor_badge = Badge.objects.get(name="instructor")

    def find_instructors(self) -> QuerySet[Person]:
        return (
            Person.objects.filter(
                award__badge__name__in=[
                    "swc-instructor",
                    "dc-instructor",
                    "lc-instructor",
                ]
            )
            .exclude(award__badge__name="instructor")
            .distinct()
        )

    def earliest_award(self, person: Person) -> Award:
        return person.award_set.order_by("awarded").first()

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
            f"Found {len(instructors)} instructors with at least one SWC/DC/LC"
            " instructor badge.",
        )

        new_awards = [
            self.create_instructor_award(instructor) for instructor in instructors
        ]
        self.log(no_output, f"Bulk-creating {len(new_awards)} new Instructor awards...")

        Award.objects.bulk_create(new_awards)
        self.log(no_output, "Done.")
