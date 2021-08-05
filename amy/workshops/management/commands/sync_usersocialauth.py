from django.core.management.base import BaseCommand
from github.GithubException import GithubException

from workshops.models import Person


class Command(BaseCommand):
    help = (
        "Synchronizes entries in UserSocialAuth with values "
        "in Person.github for given Persons."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "username", nargs="+", type=str, help="Username in AMY database"
        )

    def handle(self, *args, **options):
        """Main entry point."""

        usernames = options["username"]
        for username in usernames:
            try:
                person = Person.objects.get(username=username)
                person.synchronize_usersocialauth()
            except Person.DoesNotExist:
                print("Person not found")  # not disclosing username
            except GithubException as e:
                print(f"GitHub API exception {e}")  # not disclosing username
            else:
                print("Success")  # not disclosing username
