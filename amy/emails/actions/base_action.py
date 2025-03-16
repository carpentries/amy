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
from workshops.base_views import AuthenticatedHttpRequest

logger = logging.getLogger("amy")


def feature_flag_enabled(feature_flag: str, signal_name: str, **kwargs: Any) -> bool:
    request = kwargs.get("request")
    if not request:
        logger.debug(f"Cannot check {feature_flag} feature flag, `request` parameter to {signal_name} is missing")
        return False

    if not flag_enabled(feature_flag, request=request):  # type: ignore[no-untyped-call]
        logger.debug(f"{feature_flag} feature flag not set, skipping {signal_name}")
        return False

    return True


class BaseAction(ABC):
    """
    Base class for scheduling actions. Requires providing of the following methods:
    * `get_scheduled_at`
    * `get_context`
    * `get_context_json`
    * `get_generic_relation_object`
    * `get_recipients`
    * `get_recipients_context_json`

    All those are used in `__call__()` method to prepare an email to be scheduled and add it to the queue.

    The class instance needs to be callable (ie. define `__call__()`), because it's used in Django signal system.
    """

    signal: SignalNameEnum

    @abstractmethod
    def get_scheduled_at(self, *args: Any, **kwargs: Any) -> datetime:
        """
        Provide a specific datetime when the scheduled email should be sent out.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_context(self, *args: Any, **kwargs: Any) -> Any:
        """
        Given action kwargs, provide a concrete action context object.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_context_json(self, context: Any) -> ContextModel:
        """
        Given action context object, provide a Pydantic model ContextModel, which will be turned into JSON later.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_generic_relation_object(self, context: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Provide a single object that the scheduled email should be linked to (e.g. a person or an event
        this email is most related to). Usually use an existing object from the `context` parameter.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_recipients(self, context: Any, *args: Any, **kwargs: Any) -> list[str]:
        """
        Provide a list of email addresses of the email's recipients. Usually use an existing object(s)
        from the `context` parameter.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_recipients_context_json(self, context: Any, *args: Any, **kwargs: Any) -> ToHeaderModel:
        """
        Given action recipients list, provide a Pydantic model ToHeaderModel, which will be turned into JSON later.
        """
        raise NotImplementedError()

    def __call__(self, sender: Any, *args: Any, **kwargs: Any) -> ScheduledEmail | None:
        """
        React to Django signal and schedule an email configured by `signal` class field and the abstract
        methods.

        If the `"EMAIL_MODULE"` feature flag is not enabled, stop early.
        If `suppress_messages` bool flag is in `kwargs` and set to `True`, then no messages will be generated
        for the Django messaging system to show in the templates.
        If `dry_run` bool flag is in `kwargs` and set to `True`, then no scheduling will happen.

        Otherwise, an email will be created and scheduled to run at the specific time.
        """
        if not feature_flag_enabled("EMAIL_MODULE", self.signal, **kwargs):
            return None

        request: AuthenticatedHttpRequest = kwargs.pop("request")
        suppress_messages: bool = kwargs.pop("suppress_messages", False)
        dry_run: bool = kwargs.pop("dry_run", False)

        context = self.get_context(**kwargs)
        context_json = self.get_context_json(context)
        scheduled_at = self.get_scheduled_at(**kwargs)
        generic_relation_obj = self.get_generic_relation_object(context, **kwargs)

        try:
            if dry_run:
                logger.debug(f"Dry-run mode: email action for signal {self.signal}, {generic_relation_obj}")
                return None

            scheduled_email = EmailController.schedule_email(
                signal=self.signal,
                context_json=context_json,
                scheduled_at=scheduled_at,
                to_header=self.get_recipients(context, **kwargs),
                to_header_context_json=self.get_recipients_context_json(context, **kwargs),
                generic_relation_obj=generic_relation_obj,
                author=person_from_request(request),
            )
        except EmailControllerMissingRecipientsException:
            logger.warning(f"Missing recipients for signal {self.signal}")
            if not suppress_messages:
                messages_missing_recipients(request, self.signal)
        except EmailTemplate.DoesNotExist:
            logger.warning(f"Missing template for signal {self.signal}")
            if not suppress_messages:
                messages_missing_template(request, self.signal)
        else:
            logger.info(f"Action scheduled for signal {self.signal}")
            if not suppress_messages:
                messages_action_scheduled(request, self.signal, scheduled_email)
            return scheduled_email
        return None


class BaseActionUpdate(BaseAction):
    """
    Base class for updating scheduled emails. The same requirements as in super class `BaseAction`.

    `__call__()` method is used to update properties of a scheduled email.

    The class instance needs to be callable (ie. define `__call__()`), because it's used in Django signal system.
    """

    def __call__(self, sender: Any, *args: Any, **kwargs: Any) -> ScheduledEmail | None:
        """
        React to Django signal and update a scheduled email configured by `signal` class field and the abstract
        methods (as in the super class `BaseAction`).

        If the `"EMAIL_MODULE"` feature flag is not enabled, stop early.
        If `suppress_messages` bool flag is in `kwargs` and set to `True`, then no messages will be generated
        for the Django messaging system to show in the templates.
        If `dry_run` bool flag is in `kwargs` and set to `True`, then no scheduling will happen.

        Otherwise, an email will be updated.
        """
        if not feature_flag_enabled("EMAIL_MODULE", f"{self.signal}_update", **kwargs):
            return None

        request = kwargs.pop("request")
        suppress_messages = kwargs.pop("suppress_messages", False)
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
            logger.warning(f"Scheduled email for signal {signal_name} and {generic_relation_obj=} does not exist.")
            return None

        except ScheduledEmail.MultipleObjectsReturned:
            logger.warning(
                f"Too many scheduled emails for signal {signal_name} and "
                f"{generic_relation_obj=}. Can't update them."
            )
            return None

        try:
            if dry_run:
                logger.debug(f"Dry-run mode: email update action for signal {self.signal}, {generic_relation_obj}")
                return None

            scheduled_email = EmailController.update_scheduled_email(
                scheduled_email=scheduled_email,
                context_json=context_json,
                scheduled_at=scheduled_at,
                to_header=self.get_recipients(context, **kwargs),
                to_header_context_json=self.get_recipients_context_json(context, **kwargs),
                generic_relation_obj=generic_relation_obj,
                author=person_from_request(request),
            )
        except EmailControllerMissingRecipientsException:
            logger.warning(f"Missing recipients for signal {self.signal}")
            if not suppress_messages:
                messages_missing_recipients(request, signal_name)
        except EmailControllerMissingTemplateException:
            # Note: this is not realistically possible because the scheduled email
            # is looked up using a specific template signal.
            logger.warning(f"Template not linked to signal {self.signal}")
            if not suppress_messages:
                messages_missing_template_link(request, scheduled_email)
        else:
            logger.info(f"Action updated for signal {self.signal}")
            if not suppress_messages:
                messages_action_updated(request, signal_name, scheduled_email)
            return scheduled_email
        return None


class BaseActionCancel(BaseAction):
    """
    Base class for cancelling scheduled emails. The same requirements as in super class `BaseAction`,
    with the exception of some methods no longer being used: `get_recipients` and `get_scheduled_at`.

    `__call__()` method is used to cancel multiple matching emails.

    The class instance needs to be callable (ie. define `__call__()`), because it's used in Django signal system.
    """

    def get_recipients(self, context: Any, *args: Any, **kwargs: Any) -> list[str]:
        """Not used in BaseActionCancel."""
        raise NotImplementedError()

    def get_scheduled_at(self, *args: Any, **kwargs: Any) -> datetime:
        """Not used in BaseActionCancel."""
        raise NotImplementedError()

    def get_generic_relation_content_type(self, context: Any, generic_relation_obj: Any) -> ContentType:
        """
        Get content type object for the model of the generic relation.
        """
        return ContentType.objects.get_for_model(generic_relation_obj)

    def get_generic_relation_pk(self, context: Any, generic_relation_obj: Any) -> int | Any:
        """
        Get PK of the generic relation object.
        """
        return generic_relation_obj.pk

    def __call__(self, sender: Any, *args: Any, **kwargs: Any) -> None:
        """
        React to Django signal and cancel scheduled emails configured by `signal` class field and
        generic relation object.
        This is the only BaseAction* class that works on multiple emails.

        Generic relation object retrieval is defined through two methods:
        * `get_generic_relation_content_type`
        * `get_generic_relation_pk`
        Both can be overwritten in some rare cases.

        If the `"EMAIL_MODULE"` feature flag is not enabled, stop early.
        If `suppress_messages` bool flag is in `kwargs` and set to `True`, then no messages will be generated
        for the Django messaging system to show in the templates.
        If `dry_run` bool flag is in `kwargs` and set to `True`, then no scheduling will happen.

        Otherwise, all matching emails will be cancelled.
        """
        if not feature_flag_enabled("EMAIL_MODULE", f"{self.signal}_cancel", **kwargs):
            return

        request = kwargs["request"]
        suppress_messages = kwargs.pop("suppress_messages", False)
        dry_run = kwargs.pop("dry_run", False)

        context = self.get_context(**kwargs)
        generic_relation_obj = self.get_generic_relation_object(context, **kwargs)
        signal_name = self.signal

        generic_relation_ct = self.get_generic_relation_content_type(context, generic_relation_obj)
        generic_relation_pk = self.get_generic_relation_pk(context, generic_relation_obj)
        scheduled_emails = ScheduledEmail.objects.filter(
            generic_relation_content_type=generic_relation_ct,
            generic_relation_pk=generic_relation_pk,
            template__signal=signal_name,
            state=ScheduledEmailStatus.SCHEDULED,
        ).select_for_update()

        for scheduled_email in scheduled_emails:
            if dry_run:
                logger.debug(f"Dry-run mode: email cancel action for signal {self.signal}, {generic_relation_obj}")
                continue

            scheduled_email = EmailController.cancel_email(
                scheduled_email=scheduled_email,
                author=person_from_request(request),
            )
            logger.info(f"Action cancelled for signal {self.signal}")
            if not suppress_messages:
                messages_action_cancelled(request, signal_name, scheduled_email)
