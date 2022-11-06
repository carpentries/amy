# Automated emails

GitHub project link unavailable.

This project aims to automate sending repetitive emails, for example:

* reminders about submitting a workshop's website and slug
* thank-you emails for the instructors and hosts after workshop had run
* reminders to recruit helpers
* etc.

All these emails used to be sent by hand, now they are automatically sent on
a specific time before/after some date. For example, "Recruit Helpers" email is sent
21 days before event's start date, but only if there are no helpers on the event.


## Infrastructure

At the core of automated emails there are:

* Redis database for keeping list of scheduled actions ordered by scheduled time
* [Python RQ](https://python-rq.org/) library

Basic principle of work:

* Every scheduled action is an instance of a subclass of
  [BaseAction](https://github.com/carpentries/amy/blob/develop/amy/autoemails/actions.py#L28).
  This provides `__call__()` method for sending emails.
* When specific conditions are met, for example an instructor is added to the event,
  an instance of specific corresponding action is created and set up. Using RQ library
  that action is then scheduled to run at specific time.
* RQ library serializes (pickles) that action and puts it in Redis.
* A specific RQ worker (application running on a server) reads from the Redis looking
  for actions which should be run.
* Once the worker retrieves an action to be run, it deserializes (unpickles) it and
  calls `__call__()` method, which sends an email.


## Implementation of new actions

There's a few steps that should be taken when implementing a new action.

1. Add new action to `autoemails/actions.py` file.
    * define `get_additional_context` for defining context passed to email's template
    * implement static `check()` method for determining if the action conditions are met
      or not
2. Define template corresponding with that action, add it to
   `autoemails/fixtures/templates_triggers.json`.
3. Update `Trigger.ACTION_CHOICES` in `autoemails/models.py` with new action.
4. Provide extensive tests for the action itself (see
   `autoemails/tests/test_postworkshopaction.py` for example)
5. In views supporting changes that might trigger the action, use
   `ActionManageMixin.add()` and `ActionManageMixin.remove()` along with action's
   `check()` method (defined in step 1 above) to schedule or unschedule action email.


## Admin panel

Scheduled automated emails can be previewed in Django Admin. There are options to
reschedule, re-try if emails failed, and more.

Custom templates and views were implemented to handle this admin panel.
