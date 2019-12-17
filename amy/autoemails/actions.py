from datetime import timedelta
import logging
from typing import Optional, List, Dict

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.mail import EmailMultiAlternatives
from django.template.exceptions import (
    TemplateSyntaxError,
    TemplateDoesNotExist,
)
import django_rq

from autoemails.models import Trigger, EmailTemplate
from workshops.models import Event, Task


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
        self.template = trigger.template
        self.context_objects = objects

        # prepare logger
        self.logger = logger

        # default values for fields that will become values later on
        self.context = None
        self.email = None

    def __eq__(self, b):
        return (
            self.trigger == b.trigger and
            self.template == b.template and
            self.context_objects == b.context_objects and
            self.context == b.context and
            self.email == b.email and
            self.get_launch_at() == b.get_launch_at()
        )

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

        # refresh trigger/template DB information
        self.logger.debug('Refreshing related trigger from DB...')
        self.trigger.refresh_from_db()
        self.template = self.trigger.template

        # build email
        self.logger.debug('Building email with provided context...')
        email = self.template.build_email(context=self.context)
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
                self.email.to = [settings.AUTOEMAIL_OVERRIDE_OUTGOING_ADDRESS]
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

    # it should be at least 1 hour to give admin some time in case of mistakes
    # Shortened to 10 minutes for tests!
    #launch_at = timedelta(hours=1)
    launch_at = timedelta(minutes=10)

    @staticmethod
    def check(task: Task):
        """Conditions for creating a NewInstructorAction."""
        return (
            # 2019-11-01: we accept instructors without `may_contact` agreement
            #             because it was supposed to apply on for non-targeted
            #             communication like newsletter
            # task.person.may_contact and
            task.role.name == 'instructor' and
            task.event.tags.exclude(
                name__in=['cancelled', 'unresponsive', 'stalled']) and
            task.event in Event.objects.upcoming_events()
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
        context['person'] = task.person
        context['instructor'] = task.person
        context['role'] = task.role
        context['assignee'] = (
            event.assigned_to.full_name
            if event.assigned_to
            else 'Regional Coordinator'
        )

        return context
