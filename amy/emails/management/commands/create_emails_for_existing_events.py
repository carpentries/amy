import logging
from typing import Callable

from django.core.management.base import BaseCommand, CommandError, CommandParser
from django.db import transaction
from django.test import RequestFactory, override_settings
from django.utils import timezone

from autoemails.models import RQJob
from emails.actions.ask_for_website import (
    ask_for_website_strategy,
    run_ask_for_website_strategy,
)
from emails.actions.host_instructors_introduction import (
    host_instructors_introduction_strategy,
    run_host_instructors_introduction_strategy,
)
from emails.actions.instructor_training_approaching import (
    instructor_training_approaching_strategy,
    run_instructor_training_approaching_strategy,
)
from emails.actions.post_workshop_7days import (
    post_workshop_7days_strategy,
    run_post_workshop_7days_strategy,
)
from emails.actions.recruit_helpers import (
    recruit_helpers_strategy,
    run_recruit_helpers_strategy,
)
from emails.types import StrategyEnum
from workshops.models import Event, Person

logger = logging.getLogger("amy")


class Command(BaseCommand):
    args = "no arguments"
    help = (
        "Run strategies for email actions associated with events for all active events"
        " in the system running in the future."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--username",
            required=True,
            help="Username of existing user to be used in scheduling emails.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command in dry-run mode (no emails will be scheduled).",
        )

    def _check_conditions(
        self,
        event: Event,
        trigger_action: str,
        strategy: Callable[[Event], StrategyEnum],
    ) -> bool:
        rqjob = RQJob.objects.filter(
            event=event, trigger__action=trigger_action
        ).first()
        logger.info(f"RQJob for {event=}, {trigger_action=}: {rqjob}")

        strategy_result = strategy(event)
        return bool(
            strategy_result == StrategyEnum.CREATE
            and rqjob
            and rqjob.status == "scheduled"
        ) or bool(strategy_result == StrategyEnum.CREATE and not rqjob)

    @override_settings(FLAGS={"EMAIL_MODULE": [("boolean", True)]})
    @transaction.atomic
    def handle(self, *args, **options):
        user = Person.objects.get(username=options["username"])

        # Events must meet criteria:
        # - start date in the future
        # - not cancelled, unresponsive, or stalled
        # - has "automated-email" tag

        events = Event.objects.filter(
            start__gte=timezone.now().date(),
            tags__name="automated-email",
        ).exclude(tags__name__in=["cancelled", "unresponsive", "stalled"])

        request = RequestFactory().get("/")
        request.user = user

        for event in events:
            logger.info(f"Processing {event=}")
            try:
                # Only those strategies that are associated with events are run.

                if self._check_conditions(
                    event,
                    "ask-for-website",
                    ask_for_website_strategy,
                ):
                    run_ask_for_website_strategy(
                        StrategyEnum.CREATE,
                        request,
                        event,
                        supress_messages=True,
                        dry_run=options["dry_run"],
                    )

                if self._check_conditions(
                    event,
                    "instructors-host-introduction",
                    host_instructors_introduction_strategy,
                ):
                    run_host_instructors_introduction_strategy(
                        StrategyEnum.CREATE,
                        request,
                        event,
                        supress_messages=True,
                        dry_run=options["dry_run"],
                    )

                # No need to check RQJob - this email doesn't exists in the old system.
                run_instructor_training_approaching_strategy(
                    instructor_training_approaching_strategy(event),
                    request,
                    event,
                    supress_messages=True,
                    dry_run=options["dry_run"],
                )

                if self._check_conditions(
                    event,
                    "week-after-workshop-completion",
                    post_workshop_7days_strategy,
                ):
                    run_post_workshop_7days_strategy(
                        StrategyEnum.CREATE,
                        request,
                        event,
                        supress_messages=True,
                        dry_run=options["dry_run"],
                    )

                if self._check_conditions(
                    event,
                    "recruit-helpers",
                    recruit_helpers_strategy,
                ):
                    run_recruit_helpers_strategy(
                        StrategyEnum.CREATE,
                        request,
                        event,
                        supress_messages=True,
                        dry_run=options["dry_run"],
                    )

                logger.info(f"Ran strategies for {event=}")

            except Exception as e:
                raise CommandError(f"Error creating event for {event=}: {e}") from e
