from datetime import date, timedelta
import logging
from typing import Dict, Optional

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError
import django_rq

from autoemails.models import EmailTemplate, Trigger
from autoemails.utils import compare_emails
from consents.models import Term
from workshops.fields import TAG_SEPARATOR
from workshops.models import Event, Person, Task

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
        self.context: Optional[dict] = None
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
    def check(*args, **kwargs):
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
        try:
            return self.context_objects["event"].slug
        except (KeyError, AttributeError):
            return ""

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        try:
            return self.context_objects["task"].person.email or ""
        except (KeyError, AttributeError):
            return ""

    @staticmethod
    def check(task: Task):  # type: ignore
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
            # 2019-12-24: instead of accepting only upcoming Events, let's
            #             accept (more broadly) events starting in future
            #             or some without start date
            # 2020-01-31: slightly rewrite (less queries)
            and (not task.event.start or task.event.start >= date.today())
            # 2020-02-07: the task must have "automated-email" tag in order to
            #             be used for Email Automation
            and task.event.tags.filter(name__icontains="automated-email")
            # 2020-02-11: only for workshops administered by LC/DC/SWC
            and task.event.administrator
            and task.event.administrator.domain != "self-organized"
            and task.event.administrator.domain != "carpentries.org"
        )

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import human_daterange, match_notification_email

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
        context["tags"] = list(event.tags.values_list("name", flat=True))

        return context


class NewSupportingInstructorAction(BaseAction):
    """
    Action for informing supporting instructors about workshop they've been accepted to.

    How to use it:

    >>> triggers = Trigger.objects.filter(active=True,
                                          action='new-supporting-instructor')
    >>> for trigger in triggers:
    ...     action = NewSupportingInstructorAction(
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
        try:
            return self.context_objects["event"].slug
        except (KeyError, AttributeError):
            return ""

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        try:
            return self.context_objects["task"].person.email or ""
        except (KeyError, AttributeError):
            return ""

    @staticmethod
    def check(task: Task):  # type: ignore
        """Conditions for creating a NewSupportingInstructorAction."""
        return bool(
            task.role.name == "supporting-instructor"
            and not task.event.tags.filter(
                name__in=["cancelled", "unresponsive", "stalled"]
            )
            and (not task.event.start or task.event.start >= date.today())
            and task.event.tags.filter(name__in=["automated-email", "online"])
            and task.event.administrator
            and task.event.administrator.domain != "self-organized"
            and task.event.administrator.domain != "carpentries.org"
        )

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import human_daterange, match_notification_email

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
        context["tags"] = list(event.tags.values_list("name", flat=True))

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

    ROLES = ["host", "instructor", "supporting-instructor"]

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
        try:
            return self.context_objects["event"].slug
        except (KeyError, AttributeError):
            return ""

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        try:
            event = self.context_objects["event"]
            person_emails = list(
                Person.objects.filter(
                    task__in=event.task_set.filter(role__name__in=self.ROLES)
                )
                .distinct()
                .values_list("email", flat=True)
            )
            additional_contacts = event.contact.split(TAG_SEPARATOR)
            all_emails = list(filter(bool, person_emails + additional_contacts))
            return ", ".join(all_emails)

        except (KeyError, AttributeError):
            return ""

    @staticmethod
    def check(event: Event):  # type: ignore
        """Conditions for creating a PostWorkshopAction."""
        return bool(
            # end date is required and in future
            event.end
            and event.end >= date.today()
            # event cannot be cancelled / unresponsive / stalled
            and not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
            # 2020-02-07: changed conditions below
            # must have "automated-email" tag
            and event.tags.filter(name__icontains="automated-email")
            # must have LC, DC, or SWC tags
            and event.tags.filter(name__in=["LC", "DC", "SWC", "Circuits"])
            # must not be self-organized or instructor training
            # 2020-02-11: only for workshops administered by other than
            #             Instructor Training
            and event.administrator
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
        context["supporting_instructors"] = list(
            Person.objects.filter(
                task__in=event.task_set.filter(role__name="supporting-instructor")
            )
        )
        context["helpers"] = list(
            Person.objects.filter(task__in=event.task_set.filter(role__name="helper"))
        )
        context["hosts"] = list(
            Person.objects.filter(task__in=event.task_set.filter(role__name="host"))
        )

        # querying over Person.objects lets us get rid of duplicates
        person_emails = list(
            Person.objects.filter(
                task__in=event.task_set.filter(role__name__in=self.ROLES)
            )
            .distinct()
            .values_list("email", flat=True)
        )
        additional_contacts = event.contact.split(TAG_SEPARATOR)
        all_emails = list(filter(bool, person_emails + additional_contacts))
        context["all_emails"] = all_emails

        context["assignee"] = (
            event.assigned_to.full_name if event.assigned_to else "Regional Coordinator"
        )

        context["reports_link"] = reports_link(event.slug)
        context["tags"] = list(event.tags.values_list("name", flat=True))

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
        try:
            return self.context_objects["event"].slug
        except (KeyError, AttributeError):
            return ""

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        try:
            request = self.context_objects["request"]
            emails = [request.email] + request.additional_contact.split(TAG_SEPARATOR)
            all_emails = list(filter(bool, emails))
            return ", ".join(all_emails)
        except (KeyError, AttributeError):
            return ""

    @staticmethod
    def check(event: Event):  # type: ignore
        """Conditions for creating a SelfOrganisedRequestAction."""
        try:
            return bool(
                # is self-organized
                event.administrator
                and event.administrator.domain == "self-organized"
                # starts in future
                and event.start
                and event.start >= date.today()
                # no "cancelled", "unresponsive", or "stalled" tags
                and not event.tags.filter(
                    name__in=["cancelled", "unresponsive", "stalled"]
                )
                # special "automated-email" tag
                and event.tags.filter(name__icontains="automated-email")
                # there should be a related object `SelfOrganisedSubmission`
                and event.selforganisedsubmission
            )
        except Event.selforganisedsubmission.RelatedObjectDoesNotExist:
            # Simply accessing `event.selforganisedsubmission` to check for
            # non-None value will throw this exception :(
            return False

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import human_daterange, match_notification_email

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

        # additional contact info (see CommonRequest for details)
        emails = [request.email] + request.additional_contact.split(TAG_SEPARATOR)
        context["all_emails"] = list(filter(bool, emails))

        context["assignee"] = (
            event.assigned_to.full_name if event.assigned_to else "Regional Coordinator"
        )
        context["tags"] = list(event.tags.values_list("name", flat=True))

        return context


class InstructorsHostIntroductionAction(BaseAction):
    """
    Action for introducing centrally organised event host and instructors.

    How to use it:

    >>> triggers = Trigger.objects.filter(active=True,
                                          action='instructors-host-introduction')
    >>> for trigger in triggers:
    ...     action = InstructorsHostIntroductionAction(
    ...         trigger=trigger,
    ...         objects=dict(event=event, tasks=tasks),
    ...     )
    ...     launch_at = action.get_launch_at()
    ...     job = scheduler.enqueue_in(launch_at, action)
    """

    # Send within an hour from when the conditions are met.
    launch_at = timedelta(hours=1)

    def event_slug(self) -> str:
        """If available, return event's slug."""
        try:
            return self.context_objects["event"].slug
        except (KeyError, AttributeError):
            return ""

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        try:
            event = self.context_objects["event"]
            task_emails = [
                t.person.email
                for t in event.task_set.filter(role__name__in=["host", "instructor"])
            ]
            contacts = event.contact.split(TAG_SEPARATOR)
            all_emails = list(filter(bool, task_emails + contacts))
            return ", ".join(all_emails)
        except KeyError:
            return ""

    def recipients(self):
        """Assuming self.context is ready, overwrite email's recipients
        with selected ones."""
        try:
            return self.context["all_emails"]
        except KeyError:
            return None

    @staticmethod
    def check(event: Event):  # type: ignore
        """Conditions for creating a SelfOrganisedRequestAction."""
        # there is 1 host task and 2 instructor tasks
        try:
            host = event.task_set.filter(role__name="host").first()
            instructors = event.task_set.filter(role__name="instructor")
            supporting_instructors = event.task_set.filter(
                role__name="supporting-instructor"
            )
        except (Task.DoesNotExist, ValueError):
            return False

        online = event.tags.filter(name="online")

        return bool(
            # is NOT self-organized
            event.administrator
            and event.administrator.domain != "self-organized"
            # starts in future
            and event.start
            and event.start >= (date.today() + timedelta(days=7))
            # no "cancelled", "unresponsive", or "stalled" tags
            and not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
            # special "automated-email" tag
            and event.tags.filter(name__icontains="automated-email")
            # roles: 1 host and 2+ instructors, and perhaps 1+ supporting instr.
            and host
            and len(instructors) >= 2
            and (online and len(supporting_instructors) >= 1 or not online)
        )

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import human_daterange, match_notification_email

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
        context["dates"] = human_daterange(event.start, event.end)
        context["workshop_host"] = event.host
        context["regional_coordinator_email"] = list(match_notification_email(event))

        # people
        tasks = event.task_set.filter(
            role__name__in=["host", "instructor", "supporting-instructor"]
        ).order_by("role__name")
        hosts = tasks.filter(role__name="host")
        instructors = tasks.filter(role__name="instructor")
        support = tasks.filter(role__name="supporting-instructor")
        context["instructors"] = [instr.person for instr in instructors]
        context["supporting_instructors"] = [instr.person for instr in support]
        context["host"] = hosts[0].person
        context["hosts"] = [host.person for host in hosts]
        context["instructor1"] = instructors[0].person
        context["instructor2"] = instructors[1].person

        # supporting instructors are optional
        try:
            context["supporting_instructor1"] = support[0].person
        except IndexError:
            context["supporting_instructor1"] = None

        try:
            context["supporting_instructor2"] = support[1].person
        except IndexError:
            context["supporting_instructor2"] = None

        task_emails = [t.person.email for t in tasks]
        contacts = event.contact.split(TAG_SEPARATOR)
        context["all_emails"] = list(filter(bool, task_emails + contacts))

        context["assignee"] = (
            event.assigned_to.full_name if event.assigned_to else "Regional Coordinator"
        )
        context["tags"] = list(event.tags.values_list("name", flat=True))

        return context


class AskForWebsiteAction(BaseAction):
    """
    Action for asking centrally-organised events for the website & slug. This email
    should be sent about 1 month before the event's start date, and only if it has
    no website URL.

    How to use it:

    >>> triggers = Trigger.objects.filter(active=True,
                                          action='ask-for-slug')
    >>> for trigger in triggers:
    ...     action = AskForWebsiteAction(
    ...         trigger=trigger,
    ...         objects=dict(event=event, tasks=tasks),
    ...     )
    ...     launch_at = action.get_launch_at()
    ...     job = scheduler.enqueue_in(launch_at, action)
    """

    role_names = ["instructor", "supporting-instructor"]

    # The action should launch a month before workshop's start date
    launch_at = timedelta(days=-30)
    short_launch_at = timedelta(hours=1)

    def get_launch_at(self):
        event = self.context_objects.get("event", None)
        try:
            # If the event runs in 10 weeks (70 days), then we should get
            # timedelta(days=40) + self.short_launch_at.
            td = event.start - date.today() + self.launch_at

            # checking if td is in negative values
            if td > timedelta(0):
                return td + self.short_launch_at
            else:
                # This happens if we're already past -30days before event start.
                return self.short_launch_at

        except (AttributeError, TypeError):
            # if the event wasn't passed through, we should return default
            # timedelta() - just in case
            return self.launch_at

    def recipients(self) -> Optional[str]:
        """Assuming self.context is ready, overwrite email's recipients
        with selected ones."""
        try:
            return self.context["all_emails"]
        except (AttributeError, KeyError):
            return None

    def event_slug(self) -> str:
        """If available, return event's slug."""
        try:
            return self.context_objects["event"].slug
        except (KeyError, AttributeError):
            return ""

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        try:
            event = self.context_objects["event"]
            task_set = event.task_set.filter(role__name__in=self.role_names)
            person_emails = list(
                Person.objects.filter(task__in=task_set)
                .distinct()
                .values_list("email", flat=True)
            )
            all_emails = list(filter(bool, person_emails))
            return ", ".join(all_emails)

        except (KeyError, AttributeError):
            return ""

    @staticmethod
    def check(event: Event):  # type: ignore
        """Conditions for creating a AskForWebsiteAction."""
        instructors = event.task_set.filter(
            role__name__in=AskForWebsiteAction.role_names
        )

        return bool(
            # start date is required and in future
            event.start
            and event.start >= date.today()
            # event cannot be cancelled / unresponsive / stalled
            and not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
            # must have "automated-email" tag
            and event.tags.filter(name__icontains="automated-email")
            # must be self-organized or centrally-organised (ie. must have
            # an administrator)
            and event.administrator
            # cannot have a URL
            and not event.url
            # must have someone to send the email to
            and len(instructors) >= 1
        )

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import human_daterange, match_notification_email

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
        context["dates"] = human_daterange(event.start, event.end)
        context["workshop_host"] = event.host
        context["regional_coordinator_email"] = list(match_notification_email(event))

        # people
        instructors = event.task_set.filter(role__name__in=self.role_names)
        context["instructors"] = [instr.person for instr in instructors]
        hosts = event.task_set.filter(role__name="host")
        context["hosts"] = [host.person for host in hosts]

        task_emails = [task.person.email for task in instructors]
        context["all_emails"] = list(filter(bool, task_emails))

        context["assignee"] = (
            event.assigned_to.full_name if event.assigned_to else "Regional Coordinator"
        )
        context["tags"] = list(event.tags.values_list("name", flat=True))

        return context


class RecruitHelpersAction(BaseAction):
    """
    Action for reminding workshop organizers to recruit helpers. This email
    should be sent 21 days before the event's start date, and only if it has
    no helpers.

    How to use it:

    >>> triggers = Trigger.objects.filter(active=True,
                                          action='recruit-helpers')
    >>> for trigger in triggers:
    ...     action = RecruitHelpersAction(
    ...         trigger=trigger,
    ...         objects=dict(event=event, tasks=tasks),
    ...     )
    ...     launch_at = action.get_launch_at()
    ...     job = scheduler.enqueue_in(launch_at, action)
    """

    # The action should launch a month before workshop's start date
    launch_at = timedelta(days=-21)
    short_launch_at = timedelta(hours=1)

    def get_launch_at(self):
        event = self.context_objects.get("event", None)
        try:
            # If the event runs in 10 weeks (70 days), then we should get
            # timedelta(days=49) + self.short_launch_at.
            td = event.start - date.today() + self.launch_at

            # checking if td is in negative values
            if td > timedelta(0):
                return td + self.short_launch_at
            else:
                # This happens if we're already past -21days before event start.
                return self.short_launch_at

        except (AttributeError, TypeError):
            # if the event wasn't passed through, we should return default
            # timedelta() - just in case
            return self.launch_at

    def recipients(self) -> Optional[str]:
        """Assuming self.context is ready, overwrite email's recipients
        with selected ones."""
        try:
            return self.context["all_emails"]
        except (AttributeError, KeyError):
            return None

    def event_slug(self) -> str:
        """If available, return event's slug."""
        try:
            return self.context_objects["event"].slug
        except (KeyError, AttributeError):
            return ""

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        try:
            event = self.context_objects["event"]
            task_set = event.task_set.filter(role__name="instructor")
            person_emails = list(
                Person.objects.filter(task__in=task_set)
                .distinct()
                .values_list("email", flat=True)
            )
            all_emails = list(filter(bool, person_emails))
            return ", ".join(all_emails)

        except (KeyError, AttributeError):
            return ""

    @staticmethod
    def check(event: Event):  # type: ignore
        """Conditions for creating a RecruitHelpersAction."""
        hosts = event.task_set.filter(role__name="host")
        instructors = event.task_set.filter(role__name="instructor")
        helpers = event.task_set.filter(role__name="helper")

        return bool(
            # start date is required and in future
            event.start
            and event.start >= date.today()
            # additionally it can't be sooner than 14 days
            and (event.start - date.today()) >= timedelta(days=14)
            # event cannot be cancelled / unresponsive / stalled
            and not event.tags.filter(name__in=["cancelled", "unresponsive", "stalled"])
            # must have "automated-email" tag
            and event.tags.filter(name__icontains="automated-email")
            # must be centrally-organised
            and event.administrator
            and event.administrator.domain != "self-organized"
            # must have someone to send the email to
            and (len(instructors) >= 1 or len(hosts) >= 1)
            # can't have any helpers
            and len(helpers) == 0
        )

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import human_daterange, match_notification_email

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
        context["dates"] = human_daterange(event.start, event.end)
        context["workshop_host"] = event.host
        context["regional_coordinator_email"] = list(match_notification_email(event))

        # people
        hosts = event.task_set.filter(role__name="host")
        context["hosts"] = [host.person for host in hosts]
        instructors = event.task_set.filter(role__name="instructor")
        context["instructors"] = [instr.person for instr in instructors]

        task_emails = [
            task.person.email
            for task in event.task_set.filter(
                role__name__in=["host", "instructor"]
            ).order_by("role__name")
        ]
        context["all_emails"] = list(filter(bool, task_emails))

        context["assignee"] = (
            event.assigned_to.full_name if event.assigned_to else "Regional Coordinator"
        )
        context["tags"] = list(event.tags.values_list("name", flat=True))

        return context


class GenericAction(BaseAction):
    """
    A generic action intended for use outside of typical automated email workflows.
    It is not intended to use with any triggers.
    """

    launch_at = timedelta(hours=1)

    def event_slug(self) -> str:
        """If available, return event's slug."""
        try:
            return self.context_objects["event"].slug
        except (KeyError, AttributeError):
            return ""

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        try:
            wr = self.context_objects["request"]
            return wr.email

        except (KeyError, AttributeError):
            return ""

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import human_daterange, match_notification_email

        # prepare context
        context = dict()

        # current design allows for creating a response when there's no connected
        # event
        request = objects["request"]
        event = objects.get("event")

        context["request"] = request

        if event:
            # refresh related event if it exists
            event.refresh_from_db()
            context["workshop"] = event
            context["workshop_main_type"] = None
            tmp = event.tags.carpentries().first()
            if tmp:
                context["workshop_main_type"] = tmp.name
            context["dates"] = human_daterange(event.start, event.end)
            context["workshop_host"] = event.host
            context["regional_coordinator_email"] = list(
                match_notification_email(event)
            )

            task_emails = [
                task.person.email
                for task in event.task_set.filter(
                    role__name__in=["host", "instructor"]
                ).order_by("role__name")
            ]
            context["all_emails"] = list(filter(bool, task_emails))

            context["assignee"] = (
                event.assigned_to.full_name
                if event.assigned_to
                else "Regional Coordinator"
            )
            context["tags"] = list(event.tags.values_list("name", flat=True))

        else:
            context["assignee"] = (
                request.assigned_to.full_name
                if request.assigned_to
                else "Regional Coordinator"
            )

        return context


class NewConsentRequiredAction(BaseAction):
    """
    Action for asking users to consent to newly required terms. This email
    should be sent when a new required Term is created.

    How to use it:

    >>> triggers = Trigger.objects.filter(active=True,
                                          action='consent-required')
    >>> for trigger in triggers:
    ...     action = NewConsentRequiredAction(
    ...         trigger=trigger,
    ...         objects=dict(terms=terms),
    ...     )
    ...     launch_at = action.get_launch_at()
    ...     job = scheduler.enqueue_in(launch_at, action)
    """

    launch_at = timedelta(hours=1)

    def get_launch_at(self):
        return self.launch_at

    def recipients(self) -> Optional[str]:
        """Assuming self.context is ready, overwrite email's recipients
        with selected ones."""
        try:
            return self.context["all_emails"]
        except (AttributeError, KeyError):
            return None

    def all_recipients(self) -> str:
        """If available, return string of all recipients."""
        try:
            person_email = self.context_objects["person_email"]
            return person_email
        except (KeyError, AttributeError):
            return ""

    @staticmethod
    def check(term: Term):
        """Conditions for creating a NewConsentRequiredAction."""
        return (
            term.archived_at is None
            and term.required_type != Term.OPTIONAL_REQUIRE_TYPE
        )

    def get_additional_context(self, objects, *args, **kwargs):
        return dict()
