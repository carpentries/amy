from datetime import timedelta, date
import logging
from typing import Optional, List, Dict

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.template.exceptions import (
    TemplateSyntaxError,
    TemplateDoesNotExist,
)
import django_rq

from autoemails.models import Trigger, EmailTemplate
from autoemails.utils import compare_emails
from workshops.fields import TAG_SEPARATOR
from workshops.models import Event, Task, Person


logger = logging.getLogger("amy.signals")
scheduler = django_rq.get_scheduler("default")


class BaseAction:
    """
    Base class interface for actions triggered by our predefined triggers.
    This class can handle condition checking for whether the action should
    launch, but most importantly acts as a refresher for DB data.  It was
    intended to support lazy binding / refreshing DB data before actual email
    is built and sent out.
    """

    # Keeps the default timestamp for the job to run
    launch_at: Optional[timedelta] = None
    # Stores additional contextual data for the trigger/template
    additional_context: Optional[Dict] = None

    def __init__(self, trigger: Trigger, objects: Optional[Dict] = None):
        # save parameters just in case
        self.trigger = trigger
        # TODO: perhaps save in dict?
        self.template = trigger.template
        try:
            self.context_objects = objects.copy()
        except AttributeError:
            self.context_objects = dict()

        # prepare logger
        self.logger = logger

        # default values for fields that will become values later on
        self.context = None
        self.email = None

    def __eq__(self, b):
        try:
            return (
                self.trigger == b.trigger
                and self.template == b.template
                and self.context_objects == b.context_objects
                and self.context == b.context
                and compare_emails(self.email, b.email)
                and self.get_launch_at() == b.get_launch_at()
            )
        except AttributeError:
            return False

    @staticmethod
    def check(cls, *args, **kwargs):
        """This static method can be used to determine if conditions are met
        for creating an Action instance."""
        raise NotImplementedError()

    def get_launch_at(self, *args, **kwargs) -> Optional[timedelta]:
        return self.launch_at

    def get_additional_context(self, objects=None, *args, **kwargs) -> dict:
        if self.additional_context:
            ctx = self.additional_context.copy()
        else:
            ctx = dict()

        try:
            ctx.update(objects)
        except (TypeError, ValueError):
            pass
        return ctx

    def subject(self) -> str:
        """Overwrite in order to set own subject from descending Action."""
        return ""

    def sender(self) -> str:
        """Overwrite in order to set own sender from descending Action."""
        return ""

    def recipients(self) -> Optional[str]:
        """Overwrite in order to set own recipients from descending Action."""
        return None

    def cc_recipients(self) -> Optional[str]:
        """Overwrite in order to set own CC recipients from descending
        Action."""
        return None

    def bcc_recipients(self) -> Optional[str]:
        """Overwrite in order to set own BCC recipients from descending
        Action."""
        return None

    def reply_to(self) -> str:
        """Overwrite in order to set own reply-to from descending Action."""
        return ""

    def email_text(self) -> str:
        """Overwrite in order to set own email text body from descending
        Action."""
        return ""

    def email_html(self) -> str:
        """Overwrite in order to set own email HTML body from descending
        Action."""
        return ""

    def event_slug(self) -> str:
        """If available, return event's slug."""
        return ""

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        return ""

    def _context(self, additional_context: Optional[Dict] = None) -> Dict:
        """Prepare general context for lazy-evaluated email message used later
        on."""
        context = dict(site=Site.objects.get_current())
        if additional_context:
            context.update(additional_context)
        return context

    def _email(self, *args, **kwargs) -> EmailMultiAlternatives:
        # gather context (it should refresh all related objects from DB)
        self.logger.debug("Preparing email message context...")
        adt_context = self.get_additional_context(objects=self.context_objects)
        self.context = self._context(adt_context)

        # refresh trigger DB information
        self.logger.debug("Refreshing related trigger from DB...")
        self.trigger.refresh_from_db()
        # Don't refresh template from database!
        # self.template = self.trigger.template

        # build email
        self.logger.debug("Building email with provided context...")
        email = self.template.build_email(
            subject=self.subject(),
            sender=self.sender(),
            recipients=self.recipients(),
            cc_recipients=self.cc_recipients(),
            bcc_recipients=self.bcc_recipients(),
            reply_to=self.reply_to(),
            text=self.email_text(),
            html=self.email_html(),
            context=self.context,
        )
        return email

    def __call__(self, *args, **kwargs):
        # gather context and build email
        try:
            self.logger.debug("Preparing email to be sent...")
            self.email = self._email()

            # check if the recipients are being overridden in the settings
            if settings.AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS:
                self.logger.debug(
                    "Overriding recipient address (due to "
                    "`AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS` "
                    "setting)..."
                )
                self.email.to = [
                    str(settings.AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS),
                ]
                self.email.cc = []
                self.email.bcc = []

            # send email
            self.logger.debug("Sending email...")
            return self.email.send(fail_silently=False)
        except (
            TemplateSyntaxError,
            TemplateDoesNotExist,
            Trigger.DoesNotExist,
            EmailTemplate.DoesNotExist,
        ) as e:
            self.logger.debug("Error occurred: {}", str(e))
            return False


class NewInstructorAction(BaseAction):
    """
    Action for informing instructors about workshop they've been accepted to.

    How to use it:

    >>> triggers = Trigger.objects.filter(active=True, action='new-instructor')
    >>> for trigger in triggers:
    ...     action = NewInstructorAction(
    ...         trigger=trigger,
    ...         objects=dict(event=event, task=task),
    ...     )
    ...     launch_at = action.get_launch_at()
    ...     job = scheduler.enqueue_in(launch_at, action)
    """

    # It should be at least 1 hour to give admin some time in case of mistakes.
    launch_at = timedelta(hours=1)

    def event_slug(self) -> str:
        """If available, return event's slug."""
        return self.context_objects["event"].slug

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        return self.context_objects["task"].person.email

    @staticmethod
    def check(task: Task):
        """Conditions for creating a NewInstructorAction."""
        return bool(
            # 2019-11-01: we accept instructors without `may_contact` agreement
            #             because it was supposed to apply on for non-targeted
            #             communication like newsletter
            # task.person.may_contact and
            task.role.name == "instructor"
            and not task.event.tags.filter(
                name__in=["cancelled", "unresponsive", "stalled"]
            )
            and
            # 2019-12-24: instead of accepting only upcoming Events, let's
            #             accept (more broadly) events starting in future
            #             or some without start date
            # 2020-01-31: slightly rewrite (less queries)
            (not task.event.start or task.event.start >= date.today())
            and
            # 2020-02-07: the task must have "automated-email" tag in order to
            #             be used for Email Automation
            task.event.tags.filter(name__icontains="automated-email")
            and
            # 2020-02-11: only for workshops administered by LC/DC/SWC
            task.event.administrator
            and task.event.administrator.domain != "self-organized"
            and task.event.administrator.domain != "carpentries.org"
        )

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import (
            human_daterange,
            match_notification_email,
        )

        # refresh related event
        event = objects["event"]
        task = objects["task"]
        event.refresh_from_db()
        task.refresh_from_db()

        # prepare context
        context = dict()
        context["workshop"] = event
        context["workshop_main_type"] = None
        tmp = event.tags.carpentries().first()
        if tmp:
            context["workshop_main_type"] = tmp.name
        context["dates"] = None
        if event.start and event.end:
            context["dates"] = human_daterange(event.start, event.end)
        context["host"] = event.host
        context["regional_coordinator_email"] = list(match_notification_email(event))
        context["task"] = task
        context["person"] = task.person
        context["instructor"] = task.person
        context["role"] = task.role
        context["assignee"] = (
            event.assigned_to.full_name if event.assigned_to else "Regional Coordinator"
        )

        return context


class PostWorkshopAction(BaseAction):
    """
    Action for thanking the instructors/organizers for their work, reminding
    them about getting survey responses, and asking for any additional
    information or feedback.
    This email should be sent 7 days after the end date of an active workshop
    (not cancelled, stalled, or unresponsive).

    How to use it:

    >>> triggers = Trigger.objects.filter(active=True,
                                          action='week-after-workshop-completion')
    >>> for trigger in triggers:
    ...     action = PostWorkshopAction(
    ...         trigger=trigger,
    ...         objects=dict(event=event, tasks=tasks),
    ...     )
    ...     launch_at = action.get_launch_at()
    ...     job = scheduler.enqueue_in(launch_at, action)
    """

    # The action should launch week after workshop's end date
    launch_at = timedelta(days=7)

    def get_launch_at(self):
        event = self.context_objects.get("event", None)
        try:
            # if the event runs in 3 weeks, then we should get
            # timedelta(days=21) + self.launch_at
            # and this is correct output because `get_launch_at` returns
            # a timedelta()
            td = (event.end - date.today()) + self.launch_at

            # checking if td is in negative values
            if td > timedelta(0):
                return td
            else:
                return self.launch_at

        except (AttributeError, TypeError):
            # if the event wasn't passed through, we should return default
            # timedelta() - just in case
            return self.launch_at

    def recipients(self):
        """Assuming self.context is ready, overwrite email's recipients
        with selected ones."""
        try:
            return self.context["all_emails"]
        except (AttributeError, KeyError):
            return None

    def event_slug(self) -> str:
        """If available, return event's slug."""
        return self.context_objects["event"].slug

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        return ", ".join(
            list(
                Person.objects.filter(
                    task__in=self.context_objects["event"].task_set.filter(
                        role__name__in=["host", "instructor"]
                    )
                )
                .distinct()
                .values_list("email", flat=True)
            )
        )

    @staticmethod
    def check(event: Event):
        """Conditions for creating a PostWorkshopAction."""
        return bool(
            # end date is required and in future
            event.end
            and event.end >= date.today()
            and
            # event cannot be cancelled / unresponsive / stalled
            not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
            and
            # 2020-02-07: changed conditions below
            # must have "automated-email" tag
            event.tags.filter(name__icontains="automated-email")
            and
            # must have LC, DC, or SWC tags
            event.tags.filter(name__in=["LC", "DC", "SWC"])
            and
            # must not be self-organized or instructor training
            # 2020-02-11: only for workshops administered by other than
            #             Instructor Training
            event.administrator
            and event.administrator.domain != "carpentries.org"
        )

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import (
            human_daterange,
            match_notification_email,
            reports_link,
        )

        # refresh related event
        event = objects["event"]
        event.refresh_from_db()

        # prepare context
        context = dict()
        context["workshop"] = event
        context["workshop_main_type"] = None
        tmp = event.tags.carpentries().first()
        if tmp:
            context["workshop_main_type"] = tmp.name
        context["dates"] = None
        if event.end:
            context["dates"] = human_daterange(event.start, event.end)
        context["host"] = event.host
        context["regional_coordinator_email"] = list(match_notification_email(event))

        # to get only people from the task set
        context["instructors"] = list(
            Person.objects.filter(
                task__in=event.task_set.filter(role__name="instructor")
            )
        )
        context["helpers"] = list(
            Person.objects.filter(task__in=event.task_set.filter(role__name="helper"))
        )

        # querying over Person.objects lets us get rid of duplicates
        context["all_emails"] = list(
            Person.objects.filter(
                task__in=event.task_set.filter(role__name__in=["host", "instructor"])
            )
            .distinct()
            .values_list("email", flat=True)
        )
        context["assignee"] = (
            event.assigned_to.full_name if event.assigned_to else "Regional Coordinator"
        )

        context["reports_link"] = reports_link(event.slug)

        return context


class SelfOrganisedRequestAction(BaseAction):
    """
    Action for confirming the self-organised event being accepted. It will be
    sent an hour after the event has been accepted.

    How to use it:

    >>> triggers = Trigger.objects.filter(active=True,
                                          action='self-organised-request-form')
    >>> for trigger in triggers:
    ...     action = SelfOrganisedRequestAction(
    ...         trigger=trigger,
    ...         objects=dict(event=event, request=request),
    ...     )
    ...     launch_at = action.get_launch_at()
    ...     job = scheduler.enqueue_in(launch_at, action)
    """

    # It should be at least 1 hour to give admin some time in case of mistakes.
    launch_at = timedelta(hours=1)

    def recipients(self):
        """Assuming self.context is ready, overwrite email's recipients
        with selected ones."""
        try:
            return self.context["all_emails"]
        except (AttributeError, KeyError):
            return None

    def event_slug(self) -> str:
        """If available, return event's slug."""
        return self.context_objects["event"].slug

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        request = self.context_objects["request"]
        emails = [request.email]
        if request.additional_contact:
            for email in request.additional_contact.split(TAG_SEPARATOR):
                emails.append(email)
        return ", ".join(emails)

    @staticmethod
    def check(event: Event):
        """Conditions for creating a SelfOrganisedRequestAction."""
        try:
            return bool(
                # is self-organized
                event.administrator
                and event.administrator.domain == "self-organized"
                and
                # starts in future
                event.start
                and event.start >= date.today()
                and
                # no "cancelled", "unresponsive", or "stalled" tags
                not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
                and
                # special "automated-email" tag
                event.tags.filter(name__icontains="automated-email")
                and
                # there should be a related object `SelfOrganisedSubmission`
                event.selforganisedsubmission
            )
        except Event.selforganisedsubmission.RelatedObjectDoesNotExist:
            # Simply accessing `event.selforganisedsubmission` to check for
            # non-None value will throw this exception :(
            return False

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import match_notification_email, human_daterange

        # refresh related event and request
        event = objects["event"]
        event.refresh_from_db()
        request = objects["request"]  # SelfOrganisedSubmission
        request.refresh_from_db()

        # prepare context
        context = dict()
        context["workshop"] = event
        context["request"] = request
        context["workshop_main_type"] = None
        tmp = event.tags.carpentries().first()
        if tmp:
            context["workshop_main_type"] = tmp.name
        context["dates"] = None
        if event.end:
            context["dates"] = human_daterange(event.start, event.end)
        context["host"] = event.host
        context["regional_coordinator_email"] = list(match_notification_email(event))

        # event starts in less (or equal) than 10 days
        context["short_notice"] = event.start <= (date.today() + timedelta(days=10))

        # querying over Person.objects lets us get rid of duplicates
        context["all_emails"] = [request.email]
        # additional contact info (see CommonRequest for details)
        if request.additional_contact:
            for email in request.additional_contact.split(TAG_SEPARATOR):
                context["all_emails"].append(email)

        context["assignee"] = (
            event.assigned_to.full_name if event.assigned_to else "Regional Coordinator"
        )

        return context
