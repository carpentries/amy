import logging
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from src.communityroles.models import CommunityRole, CommunityRoleConfig
from src.workshops.models import Person

logger = logging.getLogger("amy")


class Command(BaseCommand):
    args = "no arguments"
    help = 'Create a superuser called "admin" with password "admin".'

    def handle(self, *args: Any, **options: Any) -> None:
        username = "admin"

        if Person.objects.filter(username=username).exists():
            logger.info("Admin user exists, quitting.")
            return

        try:
            admin = Person.objects.create_superuser(
                username=username,
                personal="admin",
                family="admin",
                email="admin@example.org",
                password="admin",
            )
            logger.info("Created admin user")

            role_config = CommunityRoleConfig.objects.get(name="instructor")
            CommunityRole.objects.create(
                config=role_config,
                person=admin,
            )
            logger.info("Assigned Instructor community role to admin user")

        except Exception as e:
            raise CommandError(f"Failed to create admin: {str(e)}") from e
