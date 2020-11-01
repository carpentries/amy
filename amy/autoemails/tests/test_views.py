from datetime import date

from django.test import TestCase
from django.shortcuts import reverse

from autoemails.forms import GenericEmailScheduleForm
from autoemails.models import EmailTemplate, Trigger, RQJob
from autoemails.tests.base import FakeRedisTestCaseMixin
import autoemails.views
from workshops.models import Event, Organization, WorkshopRequest, Language
from workshops.tests.base import SuperuserMixin


class TestGenericScheduleEmail(FakeRedisTestCaseMixin, SuperuserMixin, TestCase):
    def setUp(self):
        super().setUp()
        self._setUpSuperuser()

        # save scheduler and connection data
        self._saved_scheduler = autoemails.views.scheduler
        self._saved_redis_connection = autoemails.views.redis_connection
        # overwrite them
        autoemails.views.scheduler = self.scheduler
        autoemails.views.redis_connection = self.connection

    def tearDown(self):
        super().tearDown()
        autoemails.views.scheduler = self._saved_scheduler
        autoemails.views.redis_connection = self._saved_redis_connection

    def _setUpTemplateTrigger(self):
        self.template_slug = "test-template-slug"
        self.template = EmailTemplate.objects.create(
            slug=self.template_slug,
            subject="Test Email",
            to_header="{{ recipient }}",
            from_header="amy@example.org",
            body_template="# Hello there",
        )
        self.trigger = Trigger.objects.create(
            action="workshop-request-response1", template=self.template, active=True
        )

    def _setUpWorkshopRequest(self, create_event=False):
        kwargs = dict(
            state="p",
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            location="Scotland",
            country="GB",
            preferred_dates=None,
            other_preferred_dates="soon",
            language=Language.objects.get(name="English"),
            number_attendees="10-40",
            audience_description="Students of Hogwarts",
            administrative_fee="nonprofit",
            scholarship_circumstances="",
            travel_expences_management="booked",
            travel_expences_management_other="",
            institution_restrictions="no_restrictions",
            institution_restrictions_other="",
            carpentries_info_source_other="",
            user_notes="",
        )
        if create_event:
            self.event = Event.objects.create(
                slug="event1",
                start=date(2020, 10, 31),
                end=date(2020, 11, 1),
                host=Organization.objects.first(),
            )
            self.wr = WorkshopRequest.objects.create(event=self.event, **kwargs)
        else:
            self.wr = WorkshopRequest.objects.create(**kwargs)

    def _formData(self):
        return {
            "slug": "test1",
            "subject": "test2",
            "to_header": "test3",
            "from_header": "test4",
            "cc_header": "test5",
            "bcc_header": "test6",
            "reply_to_header": "test7",
            "body_template": "# test",
        }

    def test_request_method(self):
        methods = ["OPTIONS", "HEAD", "TRACE", "GET", "PUT", "PATCH", "DELETE"]
        url = reverse("autoemails:email_response", args=[1])
        for method in methods:
            with self.subTest(method=method):
                response = self.client.generic(method, path=url)
                self.assertEqual(response.status_code, 405)

        response = self.client.generic("POST", path=url)
        self.assertEqual(response.status_code, 302)  # redirect to log in

    def test_authorized(self):
        url = reverse("autoemails:email_response", args=[1])
        self.client.force_login(self.admin)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 404)

    def test_expected_objects_present_in_db(self):
        # required: a template, a trigger, and a workshop request
        self._setUpTemplateTrigger()
        self._setUpWorkshopRequest()
        url = reverse("autoemails:email_response", args=[self.wr.pk])
        data = {"slug": self.template_slug}
        self.client.force_login(self.admin)

        response = self.client.post(url, data)

        # redirects to workshop request details
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.wr.get_absolute_url())

    def test_valid_form(self):
        self._setUpTemplateTrigger()
        data = self._formData()
        form = GenericEmailScheduleForm(data, instance=self.template)

        self.assertEqual(form.is_valid(), True)

    def test_job_scheduled(self):
        self._setUpTemplateTrigger()
        self._setUpWorkshopRequest(create_event=False)
        data = self._formData()
        data.update({
            "slug": self.template_slug,
            "next": "/dashboard"
        })
        url = reverse("autoemails:email_response", args=[self.wr.pk])

        # no jobs
        self.assertEqual(self.scheduler.count(), 0)
        # no rqjobs
        self.assertFalse(RQJob.objects.all())

        self.client.force_login(self.admin)
        response = self.client.post(url, data, follow=True)

        self.assertEqual(response.status_code, 200)  # after redirect
        self.assertContains(
            response,
            "New email (Response to Workshop Request 1) was scheduled",
        )

        # 1 new job
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())

        # 1 new rqjob
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()

        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)
