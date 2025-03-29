# Base classes for scheduling, updating or cancelling receivers

## BaseAction

This class forms the base for scheduling actions related to emails. It defines common methods and attributes used in all scheduling actions.

**Abstract Methods:**

*   `get_scheduled_at(self, *args: Any, **kwargs: Any) -> datetime:` - Provides a specific datetime when the scheduled email should be sent out.  This method *must* be implemented by subclasses.
*   `get_context(self, *args: Any, **kwargs: Any) -> Any:` -  Provides a concrete action context object. This method *must* be implemented by subclasses.
*   `get_context_json(self, context: Any) -> ContextModel:` -  Provides a Pydantic model `ContextModel` that will be turned into JSON. This method *must* be implemented by subclasses.
*   `get_generic_relation_object(self, context: Any, *args: Any, **kwargs: Any) -> Any:` - Provides a single object that the scheduled email should be linked to (e.g., a person or event).  This method *must* be implemented by subclasses.
*   `get_recipients(self, context: Any, *args: Any, **kwargs: Any) -> list[str]:` - Provides a list of email addresses of the email's recipients. This method *must* be implemented by subclasses.
*   `get_recipients_context_json(self, context: Any, *args: Any, **kwargs: Any) -> ToHeaderModel:` - Provides a Pydantic model `ToHeaderModel` that will be turned into JSON. This method *must* be implemented by subclasses.

**Methods:**

*   `__call__(self, sender: Any, *args: Any, **kwargs: Any) -> ScheduledEmail | None:` - Reacts to a Django signal and schedules an email.
    *   Checks if the `"EMAIL_MODULE"` feature flag is enabled.
    *   Handles `suppress_messages` and `dry_run` flags.
    *   Calls `EmailController.schedule_email()` to schedule the email.
    *   Logs information about the scheduled action.

## BaseActionUpdate

This class extends `BaseAction` and is used for updating existing scheduled emails.

**Inherits from:** `BaseAction`

**Methods:**

*   `__call__(self, sender: Any, *args: Any, **kwargs: Any) -> ScheduledEmail | None:` - Reacts to a Django signal and updates a scheduled email.
    *   Checks if the `"EMAIL_MODULE"` feature flag is enabled.
    *   Handles `suppress_messages` and `dry_run` flags.
    *   Retrieves a `ScheduledEmail` object based on its generic relation object, template, and state.
    *   Updates the `ScheduledEmail` object using `EmailController.update_scheduled_email()`.
    *   Logs information about the updated action.
    *   Handles potential exceptions like `EmailControllerMissingRecipientsException` and `EmailControllerMissingTemplateException`.

## BaseActionCancel

This class extends `BaseAction` and is used for cancelling scheduled emails.  It's designed to handle multiple emails based on a generic relation object.

**Inherits from:** `BaseAction`

**Methods:**

*   `get_generic_relation_content_type(self, context: Any, generic_relation_obj: Any) -> ContentType:` - Gets the `ContentType` object for the model of the generic relation.
*   `get_generic_relation_pk(self, context: Any, generic_relation_obj: Any) -> int | Any:` - Gets the primary key of the generic relation object.
*   `__call__(self, sender: Any, *args: Any, **kwargs: Any) -> None:` - Reacts to a Django signal and cancels scheduled emails.
    *   Checks if the `"EMAIL_MODULE"` feature flag is enabled.
    *   Handles `suppress_messages` and `dry_run` flags.
    *   Retrieves all `ScheduledEmail` objects that match the generic relation object and have a state of `SCHEDULED`.
    *   Calls `EmailController.cancel_email()` for each scheduled email.
    *   Logs information about the cancelled action.
