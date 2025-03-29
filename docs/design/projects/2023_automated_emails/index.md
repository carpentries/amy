# Automated emails v2 (2023)

Github project: https://github.com/orgs/carpentries/projects/10

The aim of this project is to replace the current system of automated emails, which is
based on Redis and Python RQ, with a new system based on decoupled systems.
The new system should be more robust, easier to maintain, and allow for more complex
scheduling of emails, at the same time allowing to add the new types of emails more
easily.

Apart from being decoupled, another important feature of this system is that it fetches
the newest representation of objects used in the scheduled email content using AMY API,
and creating new actions is simpler and more elegant thanks to the use of
[Django signals](https://docs.djangoproject.com/en/5.0/topics/signals/).


## Infrastructure

At the core of automated emails there are:

* AMY API exposing endpoints for managing scheduled emails,
* AMY API exposing endpoints for details of objects used in emails' context,
* A separate application for accessing the AMY API and sending emails.

At the core of the new system in AMY there are used:

* Django signals for triggering actions,
* a [controller for managing scheduled emails](email_controller.md) (scheduling, rescheduling, updating,
  cancelling, etc.),
* types defined for improved type-safety,
* [base actions](./base_actions.md) classes supporting common logic for scheduling, updating or cancelling emails,
* management panel for viewing and managing scheduled emails.

## How it works

Emails can be scheduled by sending a signal with a specific
payload. There always is one signal for scheduling the email, but
some emails allow for updating or cancelling them, which is done
through two other signals.

To help deciding if an email should be sent, updated or cancelled,
these emails provide strategies, which implement checks for
conditions that should be met for the email to be sent (or updated,
or cancelled).

Once the email has been scheduled, it is stored in the database as
`ScheduledEmail` record. This record contains all the information
needed to send the email, including the email's content, the time
when it should be sent, and the email's context objects.

The context contains information about the objects that should be
used when generating MD and HTML content of the email. It consists of
model name and model's primary key, which allows to fetch the object
from the API when rendering the email.

Once emails have been scheduled, they can be retrieved by the email worker. This is
a Python lambda application that runs every 5 minutes, fetches the emails and sends
them. The accurate algorithm is described in another section.

## Email worker algorithm

After the worker sets up, it fetches all emails that should be sent by now. Then it
processes them individually asynchronously:

1. Lock the email record to prevent UI work on it.
2. Create context objects for email recipient list and email body content.
3. Create the email context with actual data from the API.
4. Create the email recipient list with actual data from the API.
5. Render the email body and subject with Jinja2 and the context.
6. Render the Markdown version of the email body (this generates the HTML).
7. Send the email.
8. Update the email record with the status.

At any step this process can fail and the email will be marked as failed. The worker
will pick it up again in the next run.

## Implementation of new actions

All actions are defined in `emails.actions` module. Each action is a class
inheriting from `BaseAction` class (for scheduling emails). If a specific action
could allow for updating or cancelling, it should consist of 2 additional classes
inheriting from `BaseActionUpdate` and `BaseActionCancel` respectively.

For details see [base actions documentation](./base_actions.md).

Each action must implement the following required methods and fields:

1. inheriting from `BaseAction`:
    * `signal` - parameter that contains a value uniquely identifying the action signal,
      and therefore also the email template
    * `get_scheduled_at()` - method that calculates when the action should be run
    * `get_context()` - method that returns the context for the email
    * `get_context_json()` - method that returns the context for the email in JSON
      format (this is used by the email worker to fetch the context from the API)
    * `get_generic_relation_object()` - method that returns the main object for the
      email (e.g. an event or a person)
    * `get_recipients()` - method that returns the list of recipients of the email
    * `get_recipients_context_json()` - method that returns the recipients of the email
      in JSON format (this is used by the email worker to fetch the recipients from the
      API)

2. inheriting from `BaseActionUpdate`:
    * the same fields and methods as in `BaseAction` class

3. inheriting from `BaseActionCancel`:
    * the same fields and methods as in `BaseAction` class, except for `get_recipients()`
      and `get_scheduled_at()` methods, which are not needed for the cancelling action,
    * optionally custom methods for providing content type model and generic relation PK are available:
      `get_generic_relation_content_type()`, `get_generic_relation_pk()`

Each base class implements a `__call__()` method that in turn uses appropriate
`EmailController` method to schedule, update, or cancel the email.
