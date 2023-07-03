from datetime import datetime

from django.db.models import Model

from emails.models import (
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)


class EmailController:
    @staticmethod
    def schedule_email(
        signal: str,
        context: dict,
        scheduled_at: datetime,
        to_header: list[str],
        generic_relation_obj: Model | None = None,
    ) -> ScheduledEmail:
        template = EmailTemplate.objects.filter(active=True).get(signal=signal)
        engine = EmailTemplate.get_engine()

        subject = EmailTemplate.render_template(engine, template.subject, context)
        body = EmailTemplate.render_template(engine, template.body, context)

        scheduled_email = ScheduledEmail.objects.create(
            state="scheduled",
            scheduled_at=scheduled_at,
            to_header=to_header,
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=subject,
            body=body,
            template=template,
            generic_relation=generic_relation_obj,
        )
        ScheduledEmailLog.objects.create(
            details=f"Scheduled {signal} to run at {scheduled_at.isoformat()}",
            state_before=None,
            state_after=ScheduledEmailStatus.SCHEDULED,
            scheduled_email=scheduled_email,
        )
        return scheduled_email

    @staticmethod
    def reschedule_email(
        scheduled_email: ScheduledEmail, new_scheduled_at: datetime
    ) -> ScheduledEmail:
        scheduled_email.scheduled_at = new_scheduled_at
        scheduled_email.save()
        ScheduledEmailLog.objects.create(
            details=f"Rescheduled email to run at {new_scheduled_at.isoformat()}",
            state_before=scheduled_email.state,
            state_after=scheduled_email.state,
            scheduled_email=scheduled_email,
        )
        return scheduled_email
