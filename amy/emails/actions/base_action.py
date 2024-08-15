from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Any

from django.contrib.contenttypes.models import ContentType
from flags.state import flag_enabled

from emails.controller import (
    EmailController,
    EmailControllerMissingRecipientsException,
    EmailControllerMissingTemplateException,
)
from emails.models import EmailTemplate, ScheduledEmail, ScheduledEmailStatus
from emails.schemas import ContextModel, ToHeaderModel
from emails.signals import SignalNameEnum
from emails.utils import (
    messages_action_cancelled,
    messages_action_scheduled,
    messages_action_updated,
    messages_missing_recipients,
    messages_missing_template,
    messages_missing_template_link,
    person_from_request,
)

logger = logging.getLogger("amy")


def feature_flag_enabled(feature_flag: str, signal_name: str, **kwargs) -> bool:
    request = kwargs.get("request")
    if not request:
        logger.debug(
            f"Cannot check {feature_flag} feature flag, `request` parameter "
            f"to {signal_name} is missing"
        )
        return False

    if not flag_enabled(feature_flag, request=request):
        logger.debug(f"{feature_flag} feature flag not set, skipping {signal_name}")
        return False

    return True


class BaseAction(ABC):
    signal: SignalNameEnum

    @abstractmethod
    def get_scheduled_at(self, **kwargs) -> datetime:
        raise NotImplementedError()

    @abstractmethod
    def get_context(self, **kwargs) -> dict[str, Any]:
        raise NotImplementedError()

    @abstractmethod
    def get_context_json(self, context: dict[str, Any]) -> ContextModel:
        raise NotImplementedError()

    @abstractmethod
    def get_generic_relation_object(self, context: dict[str, Any], **kwargs) -> Any:
        raise NotImplementedError()

    @abstractmethod
    def get_recipients(self, context: dict[str, Any], **kwargs) -> list[str]:
        raise NotImplementedError()

    @abstractmethod
    def get_recipients_context_json(
        self, context: dict[str, Any], **kwargs
    ) -> ToHeaderModel:
        raise NotImplementedError()

    def __call__(self, sender: Any, **kwargs) -> None:
        if not feature_flag_enabled("EMAIL_MODULE", self.signal, **kwargs):
            return

        request = kwargs.pop("request")
        supress_messages = kwargs.pop("supress_messages", False)
        dry_run = kwargs.pop("dry_run", False)

        context = self.get_context(**kwargs)
        context_json = self.get_context_json(context)
        scheduled_at = self.get_scheduled_at(**kwargs)
        generic_relation_obj = self.get_generic_relation_object(context, **kwargs)

        try:
            if dry_run:
                logger.debug(
                    f"Dry-run mode: email action for signal {self.signal}, "
                    f"{generic_relation_obj}"
                )
                return

            scheduled_email = EmailController.schedule_email(
                signal=self.signal,
                context_json=context_json,
                scheduled_at=scheduled_at,
                to_header=self.get_recipients(context, **kwargs),
                to_header_context_json=self.get_recipients_context_json(
                    context, **kwargs
                ),
                generic_relation_obj=generic_relation_obj,
                author=person_from_request(request),
            )
        except EmailControllerMissingRecipientsException:
            logger.warning(f"Missing recipients for signal {self.signal}")
            if not supress_messages:
                messages_missing_recipients(request, self.signal)
        except EmailTemplate.DoesNotExist:
            logger.warning(f"Missing template for signal {self.signal}")
            if not supress_messages:
                messages_missing_template(request, self.signal)
        else:
            logger.info(f"Action scheduled for signal {self.signal}")
            if not supress_messages:
                messages_action_scheduled(request, self.signal, scheduled_email)


# TODO: turn into a generic class that combines BaseAction,
#       BaseActionUpdate and BaseActionCancel for the complex signals.
class BaseActionUpdate(BaseAction):
    def __call__(self, sender: Any, **kwargs) -> None:
        if not feature_flag_enabled("EMAIL_MODULE", f"{self.signal}_update", **kwargs):
            return

        request = kwargs.pop("request")
        supress_messages = kwargs.pop("supress_messages", False)
        dry_run = kwargs.pop("dry_run", False)

        context = self.get_context(**kwargs)
        context_json = self.get_context_json(context)
        scheduled_at = self.get_scheduled_at(**kwargs)
        generic_relation_obj = self.get_generic_relation_object(context, **kwargs)
        signal_name = self.signal

        ct = ContentType.objects.get_for_model(generic_relation_obj)
        try:
            scheduled_email = (
                ScheduledEmail.objects.select_for_update()
                .select_related("template")
                .get(
                    generic_relation_content_type=ct,
                    generic_relation_pk=generic_relation_obj.pk,
                    template__signal=signal_name,
                    state=ScheduledEmailStatus.SCHEDULED,
                )
            )

        except ScheduledEmail.DoesNotExist:
            logger.warning(
                f"Scheduled email for signal {signal_name} and {generic_relation_obj=} "
                "does not exist."
            )
            return

        except ScheduledEmail.MultipleObjectsReturned:
            logger.warning(
                f"Too many scheduled emails for signal {signal_name} and "
                f"{generic_relation_obj=}. Can't update them."
            )
            return

        try:
            if dry_run:
                logger.debug(
                    f"Dry-run mode: email update action for signal {self.signal}, "
                    f"{generic_relation_obj}"
                )
                return

            scheduled_email = EmailController.update_scheduled_email(
                scheduled_email=scheduled_email,
                context_json=context_json,
                scheduled_at=scheduled_at,
                to_header=self.get_recipients(context, **kwargs),
                to_header_context_json=self.get_recipients_context_json(
                    context, **kwargs
                ),
                generic_relation_obj=generic_relation_obj,
                author=person_from_request(request),
            )
        except EmailControllerMissingRecipientsException:
            logger.warning(f"Missing recipients for signal {self.signal}")
            if not supress_messages:
                messages_missing_recipients(request, signal_name)
        except EmailControllerMissingTemplateException:
            # Note: this is not realistically possible because the scheduled email
            # is looked up using a specific template signal.
            logger.warning(f"Template not linked to signal {self.signal}")
            if not supress_messages:
                messages_missing_template_link(request, scheduled_email)
        else:
            logger.info(f"Action updated for signal {self.signal}")
            if not supress_messages:
                messages_action_updated(request, signal_name, scheduled_email)


# TODO: turn into a generic class that combines BaseAction,
#       BaseActionUpdate and BaseActionCancel for the complex signals.
class BaseActionCancel(BaseAction):
    # Method is not needed in this action.
    def get_recipients(self, context: dict[str, Any], **kwargs) -> list[str]:
        raise NotImplementedError()

    # Method is not needed in this action.
    def get_scheduled_at(self, **kwargs) -> datetime:
        raise NotImplementedError()

    def __call__(self, sender: Any, **kwargs) -> None:
        if not feature_flag_enabled("EMAIL_MODULE", f"{self.signal}_cancel", **kwargs):
            return

        request = kwargs["request"]
        supress_messages = kwargs.pop("supress_messages", False)
        dry_run = kwargs.pop("dry_run", False)

        context = self.get_context(**kwargs)
        generic_relation_obj = self.get_generic_relation_object(context, **kwargs)
        signal_name = self.signal

        ct = ContentType.objects.get_for_model(generic_relation_obj)
        scheduled_emails = ScheduledEmail.objects.filter(
            generic_relation_content_type=ct,
            generic_relation_pk=generic_relation_obj.pk,
            template__signal=signal_name,
            state=ScheduledEmailStatus.SCHEDULED,
        ).select_for_update()

        for scheduled_email in scheduled_emails:
            if dry_run:
                logger.debug(
                    f"Dry-run mode: email cancel action for signal {self.signal}, "
                    f"{generic_relation_obj}"
                )
                continue

            scheduled_email = EmailController.cancel_email(
                scheduled_email=scheduled_email,
                author=person_from_request(request),
            )
            logger.info(f"Action cancelled for signal {self.signal}")
            if not supress_messages:
                messages_action_cancelled(request, signal_name, scheduled_email)
