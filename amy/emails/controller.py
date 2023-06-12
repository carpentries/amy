from datetime import datetime

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
        from_header: str,
        reply_to_header: str,
        cc_header: list[str],
        bcc_header: list[str],
    ) -> ScheduledEmail:
        template = EmailTemplate.objects.filter(active=True).get(signal=signal)
        engine = EmailTemplate.get_engine()

        subject = EmailTemplate.render_template(engine, template.subject, context)
        body = EmailTemplate.render_template(engine, template.body, context)

        scheduled_email = ScheduledEmail.objects.create(
            state="scheduled",
            scheduled_at=scheduled_at,
            to_header=to_header,
            from_header=from_header,
            reply_to_header=reply_to_header,
            cc_header=cc_header,
            bcc_header=bcc_header,
            subject=subject,
            body=body,
            template=template,
        )
        ScheduledEmailLog.objects.create(
            details=f"Scheduled {signal} to run at {scheduled_at}",
            state_before=None,
            state_after=ScheduledEmailStatus.SCHEDULED,
            scheduled_email=scheduled_email,
        )
        return scheduled_email
