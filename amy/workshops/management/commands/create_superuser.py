from django.core.management.base import BaseCommand, CommandError

from communityroles.models import CommunityRole, CommunityRoleConfig
from workshops.models import Person


class Command(BaseCommand):
    args = "no arguments"
    help = 'Create a superuser called "admin" with password "admin".'

    def handle(self, *args, **options):
        try:
            admin = Person.objects.create_superuser(
                username="admin",
                personal="admin",
                family="admin",
                email="admin@example.org",
                password="admin",
            )
            print("Created admin user")

            role_config = CommunityRoleConfig.objects.get(name="instructor")
            CommunityRole.objects.create(
                config=role_config,
                person=admin,
            )
            print("Assigned Instructor community role to admin user")

        except Exception as e:
            raise CommandError("Failed to create admin: {0}".format(str(e)))
