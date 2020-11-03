import logging

from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
import django_rq

from workshops.models import WorkshopRequest
from workshops.util import admin_required
from .actions import GenericAction
from .forms import GenericEmailScheduleForm
from .models import EmailTemplate, Trigger
from .utils import (
    check_status,
    scheduled_execution_time,
)

logger = logging.getLogger("amy.signals")
scheduler = django_rq.get_scheduler("default")
redis_connection = django_rq.get_connection("default")


@require_POST
@admin_required
def generic_schedule_email(request, pk):
    """
    Generic view for scheduling an email to be sent.
    """
    template_slug = request.POST.get("slug", "")
    original_template = get_object_or_404(
        EmailTemplate, slug=template_slug
    )
    # Hardcoded, maybe in future respond to other requests, like
    # SelfOrganizedSubmission or WorkshopInquiry
    trigger = get_object_or_404(
        Trigger,
        action__startswith="workshop-request-response",
        template__slug=template_slug,
        active=True,
    )
    form = GenericEmailScheduleForm(request.POST, instance=original_template)
    workshop_request = get_object_or_404(WorkshopRequest, pk=pk)

    if form.is_valid():
        template = EmailTemplate(
            slug=form.cleaned_data["slug"],
            subject=form.cleaned_data["subject"],
            to_header=form.cleaned_data["to_header"],
            from_header=form.cleaned_data["from_header"],
            cc_header=form.cleaned_data["cc_header"],
            bcc_header=form.cleaned_data["bcc_header"],
            reply_to_header=form.cleaned_data["reply_to_header"],
            body_template=form.cleaned_data["body_template"],
        )

        objects = dict(request=workshop_request)
        if workshop_request.event:
            objects["event"] = workshop_request.event
            objects["workshop"] = workshop_request.event

        action = GenericAction(
            trigger=trigger,
            objects=objects,
        )
        action_name = GenericAction.__name__
        launch_at = action.get_launch_at()
        meta = dict(
            action=action,
            template=template,
            launch_at=launch_at,
            email=None,
            context=None,
        )

        job = scheduler.enqueue_in(launch_at, action, meta=meta)
        logger.debug("%s: enqueueing", action_name)
        scheduled_at = scheduled_execution_time(
            job.get_id(), scheduler=scheduler, naive=False
        )
        logger.debug("%s: job created [%r]", action_name, job)

        rqj = workshop_request.rq_jobs.create(
            job_id=job.get_id(),
            trigger=trigger,
            scheduled_execution=scheduled_at,
            status=check_status(job),
            mail_status="",
            event_slug=action.event_slug(),
            recipients=action.all_recipients(),
        )

        messages.info(
            request,
            format_html(
                "New email ({}) was scheduled to run "
                '<relative-time datetime="{}">{}</relative-time>: '
                '<a href="{}">{}</a>.',
                trigger.get_action_display(),
                scheduled_at.isoformat(),
                "{:%Y-%m-%d %H:%M}".format(scheduled_at),
                reverse("admin:autoemails_rqjob_preview", args=[rqj.pk]),
                job.id,
            ),
            fail_silently=True,
        )

        return redirect(
            request.POST.get("next", "")
            or workshop_request.get_absolute_url()
        )

    else:
        messages.error(
            request,
            f"Could not send the email due to form errors: {form.errors}",
            fail_silently=True,
        )

        return redirect(
            request.POST.get("next", "")
            or workshop_request.get_absolute_url()
        )
