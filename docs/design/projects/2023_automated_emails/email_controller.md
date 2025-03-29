## EmailController Class

This class provides methods for scheduling, rescheduling, updating, and managing scheduled emails. It interacts with email templates, attachments, and S3 storage.

### Methods

#### `schedule_email(signal, context_json, scheduled_at, to_header, to_header_context_json, generic_relation_obj=None, author=None)`

*   **Description:** Schedules a new email to be sent.
*   **Args:**
    *   `signal` (str): The signal that triggers the email.
    *   `context_json` (ContextModel): The context data for the email.
    *   `scheduled_at` (datetime): The datetime at which the email should be sent.
    *   `to_header` (list[str]): A list of recipient email addresses.
    *   `to_header_context_json` (ToHeaderModel): The context data for the recipient email addresses.
    *   `generic_relation_obj` (Model | None, optional): An optional related object. Defaults to `None`.
    *   `author` (Person | None, optional): The author of the email log entry. Defaults to `None`.
*   **Returns:** `ScheduledEmail` object.
*   **Raises:**
    *   `EmailControllerMissingRecipientsException`: If the email has no recipients.
*   **Example:**
    ```python
    # Assuming you have a ScheduledEmail object named 'scheduled_email'
    # and the necessary data in 'context_json', 'scheduled_at', etc.
    # scheduled_email = EmailController.schedule_email(
    #     signal="new_user_welcome",
    #     context_json=context_json,
    #     scheduled_at=scheduled_at,
    #     to_header=["user@example.com"],
    #     to_header_context_json=to_header_context_json,
    # )
    ```

#### `reschedule_email(scheduled_email, new_scheduled_at, author=None)`

*   **Description:** Reschedules a scheduled email at a new scheduled date.
*   **Args:**
    *   `scheduled_email` (ScheduledEmail): The ScheduledEmail object to reschedule.
    *   `new_scheduled_at` (datetime): The new datetime at which the email should be sent.
    *   `author` (Person | None, optional): The author of the email log entry. Defaults to `None`.
*   **Returns:** `ScheduledEmail` object.

#### `update_scheduled_email(scheduled_email, context_json, scheduled_at, to_header, to_header_context_json, generic_relation_obj=None, author=None)`

*   **Description:** Updates an existing scheduled email.
*   **Args:**
    *   `scheduled_email` (ScheduledEmail): The ScheduledEmail object to update.
    *   `context_json` (ContextModel): The context data for the email.
    *   `scheduled_at` (datetime): The datetime at which the email should be sent.
    *   `to_header` (list[str]): A list of recipient email addresses.
    *   `to_header_context_json` (ToHeaderModel): The context data for the recipient email addresses.
    *   `generic_relation_obj` (Model | None, optional): An optional related object. Defaults to `None`.
    *   `author` (Person | None, optional): The author of the email log entry. Defaults to `None`.
*   **Returns:** `ScheduledEmail` object.

#### `change_state_with_log(scheduled_email, new_state, details, author=None)`

*   **Description:** Changes the state of a scheduled email and logs the change.
*   **Args:**
    *   `scheduled_email` (ScheduledEmail): The ScheduledEmail object to update.
    *   `new_state` (ScheduledEmailStatus): The new state of the email.
    *   `details` (str): The details of the state change.
    *   `author` (Person | None, optional): The author of the email log entry. Defaults to `None`.
*   **Returns:** `ScheduledEmail` object.

#### `cancel_email(scheduled_email, details="Email was cancelled", author=None)`

*   **Description:** Cancels a scheduled email.
*   **Args:**
    *   `scheduled_email` (ScheduledEmail): The ScheduledEmail object to cancel.
    *   `details` (str, optional): The details of the cancellation. Defaults to "Email was cancelled".
    *   `author` (Person | None, optional): The author of the email log entry. Defaults to `None`.
*   **Returns:** `ScheduledEmail` object.

#### `lock_email(scheduled_email, details, author=None)`

*   **Description:** Locks a scheduled email.
*   **Args:**
    *   `scheduled_email` (ScheduledEmail): The ScheduledEmail object to lock.
    *   `details` (str): The details of the lock.
    *   `author` (Person | None, optional): The author of the email log entry. Defaults to `None`.
*   **Returns:** `ScheduledEmail` object.

#### `fail_email(scheduled_email, details, author=None)`

*   **Description:** Sets a scheduled email as failed.
*   **Args:**
    *   `scheduled_email` (ScheduledEmail): The ScheduledEmail object to fail.
    *   `details` (str): The details of the failure.
    *   `author` (Person | None, optional): The author of the email log entry. Defaults to `None`.
*   **Returns:** `ScheduledEmail` object.

#### `s3_file_path(scheduled_email, filename_uuid, filename)`

*   **Description:** Generates the S3 path for an attachment.
*   **Args:**
    *   `scheduled_email` (ScheduledEmail): The ScheduledEmail object.
    *   `filename_uuid` (UUID): The UUID of the attachment.
    *   `filename` (str): The filename of the attachment.
*   **Returns:** (str): The S3 path for the attachment.

#### `generate_presigned_url_for_attachment(attachment, expiration_seconds=3600)`

*   **Description:** Generates a presigned URL for an attachment.
*   **Args:**
    *   `attachment` (Attachment): The Attachment object.
    *   `expiration_seconds` (int, optional): The expiration time of the presigned URL in seconds. Defaults to 3600.
*   **Returns:** `Attachment` object.

#### `add_attachment(scheduled_email, filename, content)`

*   **Description:** Adds an attachment to a scheduled email.
*   **Args:**
    *   `scheduled_email` (ScheduledEmail): The ScheduledEmail object.
    *   `filename` (str): The filename of the attachment.
    *   `content` (bytes): The content of the attachment.
*   **Returns:** `Attachment` object.
