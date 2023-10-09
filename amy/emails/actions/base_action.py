from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Any

from flags.state import flag_enabled

from emails.controller import EmailController, EmailControllerMissingRecipientsException
from emails.models import EmailTemplate
from emails.signals import SignalNameEnum
from emails.utils import (
    messages_action_scheduled,
    messages_missing_recipients,
    messages_missing_template,
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
    def get_generic_relation_object(self, context: dict[str, Any], **kwargs) -> Any:
        raise NotImplementedError()

    @abstractmethod
    def get_recipients(self, **kwargs) -> list[str]:
        raise NotImplementedError()

    def __call__(self, sender: Any, **kwargs) -> None:
        if not feature_flag_enabled("EMAIL_MODULE", self.signal, **kwargs):
            return

        request = kwargs.pop("request")

        context = self.get_context(**kwargs)
        scheduled_at = self.get_scheduled_at(**kwargs)

        try:
            scheduled_email = EmailController.schedule_email(
                signal=self.signal,
                context=context,
                scheduled_at=scheduled_at,
                to_header=self.get_recipients(**kwargs),
                generic_relation_obj=self.get_generic_relation_object(
                    context, **kwargs
                ),
                author=person_from_request(request),
            )
        except EmailControllerMissingRecipientsException:
            messages_missing_recipients(request, self.signal)
        except EmailTemplate.DoesNotExist:
            messages_missing_template(request, self.signal)
        else:
            messages_action_scheduled(request, self.signal, scheduled_email)
