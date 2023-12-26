from datetime import datetime

from django.db.models import Model

from emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)
from emails.schemas import ContextModel, ToHeaderModel
from workshops.models import Person


class EmailControllerException(Exception):
    pass


class EmailControllerMissingRecipientsException(EmailControllerException):
    pass


class EmailControllerMissingTemplateException(EmailControllerException):
    pass


class EmailController:
    @staticmethod
    def schedule_email(
        signal: str,
        context_json: ContextModel,
        scheduled_at: datetime,
        to_header: list[str],
        to_header_context_json: ToHeaderModel,
        generic_relation_obj: Model | None = None,
        author: Person | None = None,
    ) -> ScheduledEmail:
        if not to_header:
            raise EmailControllerMissingRecipientsException(
                "Email must have at least one recipient, but `to_header` is empty."
            )

        template = EmailTemplate.objects.filter(active=True).get(signal=signal)

        # TODO: Remove this code in future [#2527]
        # No more rendering the template with provided context.
        # engine = EmailTemplate.get_engine()
        # subject = EmailTemplate.render_template(
        #     engine, template.subject, dict(context)
        # )
        # body = EmailTemplate.render_template(engine, template.body, dict(context))

        subject = template.subject
        body = template.body

        scheduled_email = ScheduledEmail.objects.create(
            state=ScheduledEmailStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            to_header=to_header,
            to_header_context_json=to_header_context_json,
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=subject,
            body=body,
            context_json=context_json,
            template=template,
            generic_relation=generic_relation_obj,
        )
        ScheduledEmailLog.objects.create(
            details=f"Scheduled {signal} to run at {scheduled_at.isoformat()}",
            state_before=None,
            state_after=ScheduledEmailStatus.SCHEDULED,
            scheduled_email=scheduled_email,
            author=author,
        )
        return scheduled_email

    @staticmethod
    def reschedule_email(
        scheduled_email: ScheduledEmail,
        new_scheduled_at: datetime,
        author: Person | None = None,
    ) -> ScheduledEmail:
        scheduled_email.scheduled_at = new_scheduled_at

        # Rescheduling a cancelled email will make it scheduled again.
        state_before = scheduled_email.state
        if scheduled_email.state == ScheduledEmailStatus.CANCELLED:
            scheduled_email.state = ScheduledEmailStatus.SCHEDULED

        scheduled_email.save()
        ScheduledEmailLog.objects.create(
            details=f"Rescheduled email to run at {new_scheduled_at.isoformat()}",
            state_before=state_before,
            state_after=scheduled_email.state,
            scheduled_email=scheduled_email,
            author=author,
        )
        return scheduled_email

    @staticmethod
    def cancel_email(
        scheduled_email: ScheduledEmail,
        author: Person | None = None,
    ) -> ScheduledEmail:
        old_state = scheduled_email.state
        scheduled_email.state = ScheduledEmailStatus.CANCELLED
        scheduled_email.save()
        ScheduledEmailLog.objects.create(
            details="Email was cancelled",
            state_before=old_state,
            state_after=scheduled_email.state,
            scheduled_email=scheduled_email,
            author=author,
        )
        return scheduled_email

    @staticmethod
    def update_scheduled_email(
        scheduled_email: ScheduledEmail,
        context_json: ContextModel,
        scheduled_at: datetime,
        to_header: list[str],
        to_header_context_json: ToHeaderModel,
        generic_relation_obj: Model | None = None,
        author: Person | None = None,
    ) -> ScheduledEmail:
        if not to_header:
            raise EmailControllerMissingRecipientsException(
                "Email must have at least one recipient, but `to_header` is empty."
            )

        template = scheduled_email.template
        if not template:
            raise EmailControllerMissingTemplateException(
                "Scheduled email must be linked to a template."
            )

        signal = template.signal

        # TODO: Remove this code in future [#2527]
        # No more rendering the template with provided context.
        # engine = EmailTemplate.get_engine()
        # subject = EmailTemplate.render_template(
        #     engine, template.subject, dict(context)
        # )
        # body = EmailTemplate.render_template(engine, template.body, dict(context))

        subject = template.subject
        body = template.body

        scheduled_email.scheduled_at = scheduled_at
        scheduled_email.subject = subject
        scheduled_email.body = body
        scheduled_email.to_header = to_header
        scheduled_email.to_header_context_json = to_header_context_json
        scheduled_email.context_json = context_json
        scheduled_email.generic_relation = generic_relation_obj
        scheduled_email.save()

        ScheduledEmailLog.objects.create(
            details=f"Updated {signal}",
            state_before=scheduled_email.state,
            state_after=scheduled_email.state,
            scheduled_email=scheduled_email,
            author=author,
        )
        return scheduled_email
