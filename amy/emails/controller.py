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
        cc_header: list[str],
        bcc_header: list[str],
        reply_to_header: str,
    ) -> ScheduledEmail:
        template = EmailTemplate.objects.filter(active=True).get(signal=signal)
        engine = EmailTemplate.get_engine()

        subject_template = engine.from_string(template.subject)
        rendered_subject = subject_template.render(context)

        body_template = engine.from_string(template.body)
        rendered_body = body_template.render(context)

        scheduled_email = ScheduledEmail.objects.create(
            state="scheduled",
            scheduled_at=scheduled_at,
            to_header=to_header,
            from_header=from_header,
            cc_header=cc_header,
            bcc_header=bcc_header,
            reply_to_header=reply_to_header,
            subject=rendered_subject,
            body=rendered_body,
            template=template,
        )
        ScheduledEmailLog.objects.create(
            details=f"Scheduled {signal} to run at {scheduled_at}",
            state_before=None,
            state_after=ScheduledEmailStatus.SCHEDULED,
            scheduled_email=scheduled_email,
        )
        return scheduled_email
