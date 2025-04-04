from datetime import datetime, timedelta
from io import BytesIO
import logging
from uuid import UUID, uuid4

import boto3
from django.conf import settings
from django.db.models import Model
from django.utils.timezone import now
import jinja2

from emails.models import (
    Attachment,
    EmailTemplate,
    ScheduledEmail,
    ScheduledEmailLog,
    ScheduledEmailStatus,
)
from emails.schemas import ContextModel, ToHeaderModel
from workshops.models import Person

s3_client = boto3.client("s3")
logger = logging.getLogger("amy")


class EmailControllerException(Exception):
    pass


class EmailControllerMissingRecipientsException(EmailControllerException):
    pass


class EmailControllerMissingTemplateException(EmailControllerException):
    pass


class EmailController:
    """
    Controller providing useful methods for managing scheduled emails and their attachments.
    """

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
        """Schedule a new email to be sent.

        Args:
            signal: The signal that triggers the email.
            context_json: The context data for the email.
            scheduled_at: The datetime at which the email should be sent.
            to_header: A list of recipient email addresses.
            to_header_context_json: The context data for the recipient email addresses.
            generic_relation_obj: An optional related object.
            author: The author of the email log entry.

        Returns:
            The created ScheduledEmail object.

        Raises:
            EmailControllerMissingRecipientsException: If the email has no recipients.
        """

        if not to_header or not to_header_context_json.root:
            raise EmailControllerMissingRecipientsException(
                "Email must have at least one recipient, but `to_header` or " "`to_header_context_json` are empty."
            )

        # Try rendering the templates with empty context to see if there are any syntax
        # errors.
        template = EmailTemplate.objects.filter(active=True).get(signal=signal)
        engine = EmailTemplate.get_engine()
        try:
            EmailTemplate.render_template(engine, template.subject, {})
        except jinja2.exceptions.UndefinedError:
            pass
        try:
            EmailTemplate.render_template(engine, template.body, {})
        except jinja2.exceptions.UndefinedError:
            pass

        subject = template.subject
        body = template.body

        scheduled_email = ScheduledEmail.objects.create(
            state=ScheduledEmailStatus.SCHEDULED,
            scheduled_at=scheduled_at,
            to_header=to_header,
            to_header_context_json=to_header_context_json.model_dump(),
            from_header=template.from_header,
            reply_to_header=template.reply_to_header,
            cc_header=template.cc_header,
            bcc_header=template.bcc_header,
            subject=subject,
            body=body,
            context_json=context_json.model_dump(),
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
        """Reschedule a scheduled email at a new scheduled date.

        Args:
            scheduled_email: The ScheduledEmail object to reschedule.
            new_scheduled_at: The new datetime at which the email should be sent.
            author: The author of the email log entry.

        Returns:
            The updated ScheduledEmail object.
        """
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
    def update_scheduled_email(
        scheduled_email: ScheduledEmail,
        context_json: ContextModel,
        scheduled_at: datetime,
        to_header: list[str],
        to_header_context_json: ToHeaderModel,
        generic_relation_obj: Model | None = None,
        author: Person | None = None,
    ) -> ScheduledEmail:
        """Update an existing scheduled email.

        Args:
            scheduled_email: The ScheduledEmail object to update.
            context_json: The context data for the email.
            scheduled_at: The datetime at which the email should be sent.
            to_header: A list of recipient email addresses.
            to_header_context_json: The context data for the recipient email addresses.
            generic_relation_obj: An optional related object.
            author: The author of the email log entry.

        Returns:
            The updated ScheduledEmail object.
        """
        if not to_header or not to_header_context_json.root:
            raise EmailControllerMissingRecipientsException(
                "Email must have at least one recipient, but `to_header` or " "`to_header_context_json` are empty."
            )

        template = scheduled_email.template
        if not template:
            raise EmailControllerMissingTemplateException("Scheduled email must be linked to a template.")

        signal = template.signal

        # Try rendering the templates with empty context to see if there are any syntax
        # errors.
        engine = EmailTemplate.get_engine()
        try:
            EmailTemplate.render_template(engine, template.subject, {})
        except jinja2.exceptions.UndefinedError:
            pass
        try:
            EmailTemplate.render_template(engine, template.body, {})
        except jinja2.exceptions.UndefinedError:
            pass

        subject = template.subject
        body = template.body

        scheduled_email.scheduled_at = scheduled_at
        scheduled_email.subject = subject
        scheduled_email.body = body
        scheduled_email.to_header = to_header
        scheduled_email.to_header_context_json = to_header_context_json.model_dump()
        scheduled_email.context_json = context_json.model_dump()
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

    @staticmethod
    def change_state_with_log(
        scheduled_email: ScheduledEmail,
        new_state: ScheduledEmailStatus,
        details: str,
        author: Person | None = None,
    ) -> ScheduledEmail:
        """Change the state of a scheduled email and logs the change.

        Args:
            scheduled_email: The ScheduledEmail object to update.
            new_state: The new state of the email.
            details: The details of the state change.
            author: The author of the email log entry.

        Returns:
            The updated ScheduledEmail object.
        """
        old_state = scheduled_email.state
        scheduled_email.state = new_state
        scheduled_email.save()
        ScheduledEmailLog.objects.create(
            details=details,
            state_before=old_state,
            state_after=scheduled_email.state,
            scheduled_email=scheduled_email,
            author=author,
        )
        return scheduled_email

    @staticmethod
    def cancel_email(
        scheduled_email: ScheduledEmail,
        details: str = "Email was cancelled",
        author: Person | None = None,
    ) -> ScheduledEmail:
        """Cancel a scheduled email.

        Args:
            scheduled_email: The ScheduledEmail object to cancel.
            details: The details of the cancellation.
            author: The author of the email log entry.

        Returns:
            The updated ScheduledEmail object.
        """
        return EmailController.change_state_with_log(scheduled_email, ScheduledEmailStatus.CANCELLED, details, author)

    @staticmethod
    def lock_email(scheduled_email: ScheduledEmail, details: str, author: Person | None = None) -> ScheduledEmail:
        """Lock a scheduled email.

        Args:
            scheduled_email: The ScheduledEmail object to lock.
            details: The details of the lock.
            author: The author of the email log entry.

        Returns:
            The updated ScheduledEmail object.
        """
        return EmailController.change_state_with_log(scheduled_email, ScheduledEmailStatus.LOCKED, details, author)

    @staticmethod
    def fail_email(scheduled_email: ScheduledEmail, details: str, author: Person | None = None) -> ScheduledEmail:
        """Set a scheduled email as failed.

        Args:
            scheduled_email: The ScheduledEmail object to fail.
            details: The details of the failure.
            author: The author of the email log entry.

        Returns:
            The updated ScheduledEmail object.
        """
        email = EmailController.change_state_with_log(scheduled_email, ScheduledEmailStatus.FAILED, details, author)

        # Count the number of failures. If it's >= MAX_FAILED_ATTEMPTS, then cancel
        # the email.
        latest_status_changes = ScheduledEmailLog.objects.filter(scheduled_email=email).order_by("-created_at")[
            : 2 * settings.EMAIL_MAX_FAILED_ATTEMPTS
        ]
        # 2* because the worker first locks the email, then it fails it.
        # We don't want to cancel an email which was cancelled, and then the user
        # decided to reschedule it.

        failed_attempts_count = len(
            [log for log in latest_status_changes if log.state_after == ScheduledEmailStatus.FAILED]
        )
        if failed_attempts_count >= settings.EMAIL_MAX_FAILED_ATTEMPTS:
            email = EmailController.cancel_email(
                email,
                f"Email failed {failed_attempts_count} times, cancelling.",
                author,
            )

        return email

    @staticmethod
    def succeed_email(scheduled_email: ScheduledEmail, details: str, author: Person | None = None) -> ScheduledEmail:
        """Set a scheduled email as succeeded.

        Args:
            scheduled_email: The ScheduledEmail object to succeed.
            details: The details of the success.
            author: The author of the email log entry.

        Returns:
            The updated ScheduledEmail object.
        """
        return EmailController.change_state_with_log(scheduled_email, ScheduledEmailStatus.SUCCEEDED, details, author)

    @staticmethod
    def s3_file_path(scheduled_email: ScheduledEmail, filename_uuid: UUID, filename: str) -> str:
        """Generate the S3 path for an attachment.

        Args:
            scheduled_email: The ScheduledEmail object.
            filename_uuid: The UUID of the attachment.
            filename: The filename of the attachment.

        Returns:
            The S3 path for the attachment.
        """
        return f"{scheduled_email.pk}/{filename_uuid}-{filename}"

    @staticmethod
    def add_attachment(scheduled_email: ScheduledEmail, filename: str, content: bytes) -> Attachment:
        """Add an attachment to a scheduled email.

        Args:
            scheduled_email: The ScheduledEmail object.
            filename: The filename of the attachment.
            content: The content of the attachment.

        Returns:
            The created Attachment object.
        """
        bucket_name = settings.EMAIL_ATTACHMENTS_BUCKET_NAME

        attachment_uuid = uuid4()
        s3_path = EmailController.s3_file_path(scheduled_email, attachment_uuid, filename)
        logger.debug(f"S3 Bucket for attachment upload: {bucket_name}")
        logger.debug(f"Path for attachment upload: {s3_path}")

        with BytesIO(content) as data:
            s3_client.upload_fileobj(data, bucket_name, s3_path)
            logger.info(f"File {s3_path} uploaded to S3 bucket {bucket_name}.")

        attachment = Attachment.objects.create(
            id=attachment_uuid,
            email=scheduled_email,
            filename=filename,
            s3_path=s3_path,
            s3_bucket=bucket_name,
        )
        logger.info(f"Attachment {attachment_uuid} assigned to {scheduled_email=}")
        return attachment

    @staticmethod
    def generate_presigned_url_for_attachment(attachment: Attachment, expiration_seconds: int = 3600) -> Attachment:
        """Generate a presigned URL for an attachment. It's needed for unauthorized users to
        be able to download the attachment from S3.

        Args:
            attachment: The Attachment object.
            expiration_seconds: The expiration time of the presigned URL in seconds.

        Returns:
            The updated Attachment object.
        """
        logger.debug(f"Requesting presigned URL for attachment: {attachment}")

        expiration = now() + timedelta(seconds=expiration_seconds)
        response = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": attachment.s3_bucket or settings.EMAIL_ATTACHMENTS_BUCKET_NAME,
                "Key": attachment.s3_path,
            },
            ExpiresIn=expiration_seconds,
        )

        logger.debug(f"Presigned URL {response=}, {expiration=}")
        attachment.presigned_url = response
        attachment.presigned_url_expiration = expiration
        attachment.save()

        return attachment
