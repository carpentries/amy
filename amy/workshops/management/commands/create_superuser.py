from django.core.management.base import BaseCommand, CommandError
from django.utils.crypto import get_random_string

from communityroles.models import CommunityRole, CommunityRoleConfig
from workshops.models import Person


class Command(BaseCommand):
    args = "no arguments"
    help = 'Create a superuser called "admin" with password "admin".'

    def add_arguments(self, parser):
        parser.add_argument(
            "--random-password",
            action="store_true",
            help="Use randomly generated password for the superuser",
        )

    def _random_password(self) -> str:
        return get_random_string(length=40)

    def handle(self, *args, **options):
        username = "admin"
        password = (options["random_password"] and self._random_password()) or "admin"
        email = "admin@example.org"

        if Person.objects.filter(username=username).exists():
            print("Admin user exists, quitting.")
            return

        try:
            print("Attempting to create admin user")
            admin = Person.objects.create_superuser(
                username=username,
                personal="admin",
                family="admin",
                email=email,
                password=password,
            )
            print(f"Created admin user with password {password}")

            role_config = CommunityRoleConfig.objects.get(name="instructor")
            CommunityRole.objects.create(
                config=role_config,
                person=admin,
            )
            print("Assigned Instructor community role to admin user")

        except Exception as e:
            raise CommandError("Failed to create admin: {0}".format(str(e)))
