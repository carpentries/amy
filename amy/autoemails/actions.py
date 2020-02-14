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
from workshops.models import Event, Task, Person


logger = logging.getLogger('amy.signals')
scheduler = django_rq.get_scheduler('default')


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
                self.trigger == b.trigger and
                self.template == b.template and
                self.context_objects == b.context_objects and
                self.context == b.context and
                compare_emails(self.email, b.email) and
                self.get_launch_at() == b.get_launch_at()
            )
        except AttributeError:
            return False

    @staticmethod
    def check(cls, *args, **kwargs):
        """This static method can be used to determine if conditions are met
        for creating an Action instance."""
        raise NotImplementedError()

    def get_launch_at(self, *args, **kwargs):
        return self.launch_at

    def get_additional_context(self, objects=None, *args, **kwargs):
        if self.additional_context:
            ctx = self.additional_context.copy()
        else:
            ctx = dict()

        try:
            ctx.update(objects)
        except (TypeError, ValueError):
            pass
        return ctx

    def subject(self):
        """Overwrite in order to set own subject from descending Action."""
        return ""

    def sender(self):
        """Overwrite in order to set own sender from descending Action."""
        return ""

    def recipients(self):
        """Overwrite in order to set own recipients from descending Action."""
        return None

    def cc_recipients(self):
        """Overwrite in order to set own CC recipients from descending
        Action."""
        return None

    def bcc_recipients(self):
        """Overwrite in order to set own BCC recipients from descending
        Action."""
        return None

    def reply_to(self):
        """Overwrite in order to set own reply-to from descending Action."""
        return ""

    def email_text(self):
        """Overwrite in order to set own email text body from descending
        Action."""
        return ""

    def email_html(self):
        """Overwrite in order to set own email HTML body from descending
        Action."""
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
        self.logger.debug('Preparing email message context...')
        adt_context = self.get_additional_context(objects=self.context_objects)
        self.context = self._context(adt_context)

        # refresh trigger DB information
        self.logger.debug('Refreshing related trigger from DB...')
        self.trigger.refresh_from_db()
        # Don't refresh template from database!
        # self.template = self.trigger.template

        # build email
        self.logger.debug('Building email with provided context...')
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
            self.logger.debug('Preparing email to be sent...')
            self.email = self._email()

            # check if the recipients are being overridden in the settings
            if settings.AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS:
                self.logger.debug('Overriding recipient address (due to '
                                  '`AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS` '
                                  'setting)...')
                self.email.to = [
                    str(settings.AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS),
                ]
                self.email.cc = []
                self.email.bcc = []

            # send email
            self.logger.debug('Sending email...')
            return self.email.send(fail_silently=False)
        except (TemplateSyntaxError, TemplateDoesNotExist,
                Trigger.DoesNotExist, EmailTemplate.DoesNotExist) as e:
            self.logger.debug('Error occurred: {}', str(e))
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
    # launch_at = timedelta(hours=1)
    # Shortened to 10 minutes for tests!
    launch_at = timedelta(minutes=10)

    @staticmethod
    def check(task: Task):
        """Conditions for creating a NewInstructorAction."""
        return bool(
            # 2019-11-01: we accept instructors without `may_contact` agreement
            #             because it was supposed to apply on for non-targeted
            #             communication like newsletter
            # task.person.may_contact and
            task.role.name == 'instructor' and
            not task.event.tags.filter(name__in=[
                'cancelled', 'unresponsive', 'stalled'
            ]) and
            # 2019-12-24: instead of accepting only upcoming Events, let's
            #             accept (more broadly) events starting in future
            #             or some without start date
            # 2020-01-31: slightly rewrite (less queries)
            (not task.event.start or task.event.start >= date.today()) and
            # 2020-02-07: the task must have "automated-email" tag in order to
            #             be used for Email Automation
            task.event.tags.filter(name__icontains='automated-email') and
            # 2020-02-11: only for workshops administered by LC/DC/SWC
            task.event.administrator and
            task.event.administrator.domain != 'self-organized' and
            task.event.administrator.domain != 'carpentries.org'
        )

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import match_notification_email, human_daterange

        # refresh related event
        event = objects['event']
        task = objects['task']
        event.refresh_from_db()
        task.refresh_from_db()

        # prepare context
        context = dict()
        context['workshop'] = event
        context['workshop_main_type'] = None
        tmp = event.tags.carpentries().first()
        if tmp:
            context['workshop_main_type'] = tmp.name
        context['dates'] = None
        if event.start and event.end:
            context['dates'] = human_daterange(event.start, event.end)
        context['host'] = event.host
        context['regional_coordinator_email'] = \
            list(match_notification_email(event))
        context['task'] = task
        context['person'] = task.person
        context['instructor'] = task.person
        context['role'] = task.role
        context['assignee'] = (
            event.assigned_to.full_name
            if event.assigned_to
            else 'Regional Coordinator'
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
    # launch_at = timedelta(days=7)
    # Shortened to 10 minutes for tests!
    launch_at = timedelta(minutes=10)

    def get_launch_at(self):
        event = self.context_objects.get('event', None)
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
            return self.context['all_emails']
        except (AttributeError, KeyError):
            return None

    @staticmethod
    def check(event: Event):
        """Conditions for creating a PostWorkshopAction."""
        return bool(
            # end date is required and in future
            event.end and
            event.end >= date.today() and
            # event cannot be cancelled / unresponsive / stalled
            not event.tags.filter(name__in=[
                'cancelled', 'unresponsive', 'stalled'
            ]) and
            # 2020-02-07: changed conditions below
            # must have "automated-email" tag
            event.tags.filter(name__icontains='automated-email') and
            # must have LC, DC, or SWC tags
            event.tags.filter(name__in=['LC', 'DC', 'SWC']) and
            # must not be self-organized or instructor training
            # 2020-02-11: only for workshops administered by other than
            #             Instructor Training
            event.administrator and
            event.administrator.domain != 'carpentries.org'
        )

    def get_additional_context(self, objects, *args, **kwargs):
        from workshops.util import match_notification_email, human_daterange

        # refresh related event
        event = objects['event']
        event.refresh_from_db()

        # prepare context
        context = dict()
        context['workshop'] = event
        context['workshop_main_type'] = None
        tmp = event.tags.carpentries().first()
        if tmp:
            context['workshop_main_type'] = tmp.name
        context['dates'] = None
        if event.end:
            context['dates'] = human_daterange(event.start, event.end)
        context['host'] = event.host
        context['regional_coordinator_email'] = \
            list(match_notification_email(event))

        # to get only people from the task set
        context['helpers'] = list(
            Person.objects.filter(
                task__in=event.task_set.filter(role__name='helper')
            )
        )
        # querying over Person.objects lets us get rid of duplicates
        context['all_emails'] = list(
            Person.objects.filter(
                task__in=event.task_set.filter(
                    role__name__in=['host', 'instructor']
                )
            ).distinct().values_list('email', flat=True)
        )
        context['assignee'] = (
            event.assigned_to.full_name
            if event.assigned_to
            else 'Regional Coordinator'
        )

        return context
