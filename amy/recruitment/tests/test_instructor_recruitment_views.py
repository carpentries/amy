from datetime import date, timedelta
from unittest import mock
from urllib.parse import quote

from django.http import Http404
from django.test import override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from autoemails.actions import (
    DeclinedInstructorsAction,
    InstructorsHostIntroductionAction,
    NewInstructorAction,
)
from autoemails.models import EmailTemplate, RQJob, Trigger
from autoemails.tests.base import FakeRedisTestCaseMixin
from communityroles.models import (
    CommunityRole,
    CommunityRoleConfig,
    CommunityRoleInactivation,
)
from recruitment.filters import InstructorRecruitmentFilter
from recruitment.forms import (
    InstructorRecruitmentAddSignupForm,
    InstructorRecruitmentCreateForm,
    InstructorRecruitmentSignupChangeStateForm,
)
from recruitment.models import (
    InstructorRecruitment,
    InstructorRecruitmentSignup,
    RecruitmentPriority,
)
import recruitment.views
from recruitment.views import (
    InstructorRecruitmentAddSignup,
    InstructorRecruitmentChangeState,
    InstructorRecruitmentCreate,
    InstructorRecruitmentDetails,
    InstructorRecruitmentList,
    InstructorRecruitmentSignupChangeState,
)
from workshops.models import (
    Event,
    Language,
    Organization,
    Person,
    Role,
    Tag,
    Task,
    WorkshopRequest,
)
from workshops.tests.base import TestBase


class TestInstructorRecruitmentListView(TestBase):
    def test_class_fields(self) -> None:
        # Arrange
        view = InstructorRecruitmentList()
        # Assert
        self.assertEqual(
            view.permission_required, "recruitment.view_instructorrecruitment"
        )
        self.assertEqual(view.title, "Recruitment processes")
        self.assertEqual(view.filter_class, InstructorRecruitmentFilter)
        self.assertEqual(
            view.template_name, "recruitment/instructorrecruitment_list.html"
        )
        self.assertNotEqual(view.queryset, None)  # it's a complicated query

    def test_get_filter_data(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        request.user = mock.MagicMock()
        view = InstructorRecruitmentList(request=request)
        # Act
        data = view.get_filter_data()
        # Assert
        self.assertIn("assigned_to", data.keys())
        self.assertEqual(data["assigned_to"], request.user.pk)

    def test_get_context_data_empty(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        request.user = mock.MagicMock()
        view = InstructorRecruitmentList(request=request, object_list=[], filter=None)
        # Act
        context = view.get_context_data()
        # Assert
        self.assertIn("personal_conflicts", context.keys())
        self.assertEqual(
            list(context["personal_conflicts"]), list(Person.objects.none())
        )

    def test_get_context_data(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        request.user = mock.MagicMock()
        view = InstructorRecruitmentList(request=request, object_list=[], filter=None)
        host = Organization.objects.first()
        event = Event.objects.create(slug="test-event", host=host)
        recruitment = InstructorRecruitment.objects.create(event=event)
        person = Person.objects.create(username="test_user")
        InstructorRecruitmentSignup.objects.create(
            recruitment=recruitment, person=person, interest="session"
        )
        # Act
        context = view.get_context_data()
        # Assert
        self.assertEqual(list(context["personal_conflicts"]), [person])

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
            start=date(2022, 1, 22),
        )
        recruitment = InstructorRecruitment.objects.create(
            assigned_to=self.admin,
            event=event,
            notes="Test notes",
        )
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        signup = InstructorRecruitmentSignup.objects.create(
            recruitment=recruitment, person=person, interest="session"
        )
        # Act
        response = self.client.get(reverse("all_instructorrecruitment"))
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["object_list"]), [recruitment])
        self.assertEqual(
            list(response.context["object_list"][0].signups.all()),
            [signup],
        )


class TestInstructorRecruitmentCreateView(TestBase):
    def prepare_event(self) -> Event:
        organization = Organization.objects.first()
        return Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
            start=date.today(),
            venue="Hogwarts",
            latitude=90.0,
            longitude=90.0,
        )

    def test_class_fields(self) -> None:
        # Arrange
        view = InstructorRecruitmentCreate()
        # Assert
        self.assertEqual(
            view.permission_required, "recruitment.add_instructorrecruitment"
        )
        self.assertEqual(view.model, InstructorRecruitment)
        self.assertEqual(
            view.template_name, "recruitment/instructorrecruitment_add.html"
        )
        self.assertEqual(view.form_class, InstructorRecruitmentCreateForm)

    def test_get_other_object(self) -> None:
        # Arrange
        host = Organization.objects.first()
        online_tag = Tag.objects.get(name="online")
        data = [
            (Event(slug="test1", host=host, start=date(2000, 1, 1)), False),
            (Event.objects.create(slug="test2", host=host, start=date.today()), False),
            (Event.objects.create(slug="test3", host=host, start=date.today()), True),
            (
                Event.objects.create(
                    slug="test4", host=host, start=date.today(), venue="University"
                ),
                False,
            ),
            (
                Event.objects.create(
                    slug="test5",
                    host=host,
                    start=date.today(),
                    venue="University",
                    latitude=1,
                ),
                False,
            ),
            (
                Event.objects.create(
                    slug="test6",
                    host=host,
                    start=date.today(),
                    venue="University",
                    latitude=1,
                    longitude=-1,
                ),
                True,
            ),
            (
                Event.objects.create(slug="test1", host=host, start=date(2000, 1, 1)),
                False,
            ),
        ]
        data[2][0].tags.add(online_tag)
        data[6][0].tags.add(online_tag)

        for event, expected in data:
            # Act
            view = InstructorRecruitmentCreate(kwargs={"event_id": event.pk})

            # Assert
            if expected:
                object = view.get_other_object()
                self.assertEqual(event.pk, object.pk)
            else:
                with self.assertRaises(Http404):
                    view.get_other_object()

    def test_get(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        event = self.prepare_event()
        view = InstructorRecruitmentCreate(kwargs={"event_id": event.pk})
        # Act
        with mock.patch("recruitment.views.super") as mock_super:
            view.get(request)
        # Assert
        self.assertEqual(view.request, request)
        self.assertEqual(view.event, event)
        mock_super().get.assert_called_once_with(request)

    def test_post(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        event = self.prepare_event()
        view = InstructorRecruitmentCreate(kwargs={"event_id": event.pk})
        # Act
        with mock.patch("recruitment.views.super") as mock_super:
            view.post(request)
        # Assert
        self.assertEqual(view.request, request)
        self.assertEqual(view.event, event)
        mock_super().post.assert_called_once_with(request)

    def test_get_form_kwargs(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        event = self.prepare_event()
        view = InstructorRecruitmentCreate(request=request)
        view.event = event
        # Act
        kwargs = view.get_form_kwargs()
        # Assert
        self.assertEqual(kwargs, {"initial": {}, "prefix": "instructorrecruitment"})

    def test_context_data(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        event = self.prepare_event()
        view = InstructorRecruitmentCreate(request=request, object=None)
        view.event = event
        # Act
        context = view.get_context_data()
        # Assert
        self.assertEqual(
            context,
            {
                "title": "Begin Instructor Selection Process for test-event",
                "event": event,
                "event_dates": event.human_readable_date(
                    common_month_left=r"%B %d", separator="-"
                ),
                "view": view,
                "model": InstructorRecruitment,
                # it needs to be the same instance, otherwise the test fails
                "form": context["form"],
                "priority": RecruitmentPriority.HIGH,
            },
        )

    def test_get_initial(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        event = self.prepare_event()
        workshop_request = WorkshopRequest.objects.create(
            event=event,
            personal="Harry",
            family="Potter",
            email="harry@hogwarts.edu",
            institution_other_name="Hogwarts",
            location="Scotland",
            country="GB",
            audience_description="Students of Hogwarts",
            user_notes="Only Gryffindor allowed.",
            number_attendees="10-40",
            administrative_fee="nonprofit",
            language=Language.objects.get(name="English"),
        )
        view = InstructorRecruitmentCreate(request=request, object=None)
        view.event = event
        # Act
        initial = view.get_initial()
        # Assert
        self.assertEqual(
            initial,
            {
                "notes": f"{workshop_request.audience_description}\n\n"
                f"{workshop_request.user_notes}",
            },
        )

    def test_form_valid(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        request.user = mock.MagicMock()
        mock_form = mock.MagicMock()
        event = self.prepare_event()
        view = InstructorRecruitmentCreate(request=request)
        view.event = event
        # Act
        with mock.patch("recruitment.views.super") as mock_super:
            view.form_valid(mock_form)
        # Assert
        mock_form.save.assert_called_once_with(commit=False)
        self.assertEqual(view.object.event, event)
        mock_super().form_valid.assert_called_once_with(mock_form)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        event = self.prepare_event()
        data = {"instructorrecruitment-notes": "Test notes"}
        # Act
        response = self.client.post(
            reverse("instructorrecruitment_add", args=[event.pk]), data, follow=True
        )
        recruitment: InstructorRecruitment = response.context["object"]
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.redirect_chain,
            [
                (
                    reverse(
                        "instructorrecruitment_details",
                        args=[recruitment.pk],
                    ),
                    302,
                )
            ],
        )
        self.assertEqual(recruitment.status, "o")
        self.assertEqual(recruitment.notes, "Test notes")
        self.assertEqual(recruitment.event, event)


class TestInstructorRecruitmentDetailsView(TestBase):
    def test_class_fields(self) -> None:
        # Arrange
        view = InstructorRecruitmentDetails()
        # Assert
        self.assertEqual(
            view.permission_required, "recruitment.view_instructorrecruitment"
        )
        self.assertNotEqual(view.queryset, None)  # actual qs is quite lengthy
        self.assertEqual(
            view.template_name, "recruitment/instructorrecruitment_details.html"
        )

    def test_context_data(self) -> None:
        # Arrange
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
            start=date(2021, 12, 29),
        )
        recruitment = InstructorRecruitment.objects.create(
            event=event,
            notes="Test notes",
        )
        view = InstructorRecruitmentDetails(
            kwargs={"pk": recruitment.pk}, object=recruitment
        )
        # Act
        context = view.get_context_data()
        # Assert
        self.assertEqual(
            context,
            {
                "title": str(recruitment),
                "instructorrecruitment": recruitment,
                "object": recruitment,
                "view": view,
            },
        )

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
            start=date(2021, 12, 29),
        )
        recruitment = InstructorRecruitment.objects.create(
            event=event,
            notes="Test notes",
        )
        # Act
        response = self.client.get(
            reverse("instructorrecruitment_details", args=[recruitment.pk])
        )
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["object"], recruitment)


class TestInstructorRecruitmentAddSignup(TestBase):
    def test_class_fields(self) -> None:
        # Arrange
        view = InstructorRecruitmentAddSignup()
        # Assert
        self.assertEqual(
            view.permission_required,
            [
                "recruitment.change_instructorrecruitment",
                "recruitment.view_instructorrecruitmentsignup",
            ],
        )
        self.assertEqual(view.form_class, InstructorRecruitmentAddSignupForm)
        self.assertEqual(
            view.template_name, "recruitment/instructorrecruitment_add_signup.html"
        )

    def test_context_data(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
            start=date(2021, 12, 29),
        )
        recruitment = InstructorRecruitment.objects.create(
            event=event,
            notes="Test notes",
        )
        view = InstructorRecruitmentAddSignup(
            kwargs={"pk": recruitment.pk},
            object=recruitment,
            request=request,
        )
        # Act
        context = view.get_context_data(form=None)
        # Assert
        self.assertEqual(
            context,
            {
                "form": None,
                "title": f"Add instructor application to {recruitment}",
                "view": view,
            },
        )

    def test_get_object(self) -> None:
        # Arrange
        pk = 120000
        view = InstructorRecruitmentAddSignup(kwargs={"pk": pk})
        # Act
        with mock.patch("recruitment.views.InstructorRecruitment") as mock_recruitment:
            view.get_object()
        # Assert
        mock_recruitment.objects.get.assert_called_once_with(pk=pk)

    def test_get_success_url(self) -> None:
        # Arrange
        url_redirect = {
            "/asdasd": "/asdasd",
            "/asdasd?status=o": "/asdasd?status=o",
            "https://google.com/": reverse("all_instructorrecruitment"),
            None: reverse("all_instructorrecruitment"),
        }
        for url, redirect in url_redirect.items():
            request = RequestFactory().post(f"/?next={quote(url)}" if url else "/")
            pk = 120000
            view = InstructorRecruitmentAddSignup(kwargs={"pk": pk})
            with mock.patch("recruitment.views.InstructorRecruitment"):
                view.post(request)
            # Act
            result = view.get_success_url()
            # Assert
            self.assertEqual(result, redirect)

    def test_get_success_message(self) -> None:
        # Arrange
        view = InstructorRecruitmentAddSignup(object="Test")
        data = {
            "person": "Harry Potter",
            "other_data": "James Bond",
        }
        # Act
        success_message = view.get_success_message(data)
        # Assert
        self.assertEqual(success_message, "Added Harry Potter to Test")

    def test_form_valid(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        mock_object = mock.MagicMock()
        view = InstructorRecruitmentAddSignup(object=mock_object, request=request)
        form = mock.MagicMock()
        mock_signup = mock.MagicMock()
        form.save.return_value = mock_signup

        # Act
        with mock.patch("recruitment.views.super") as mock_super:
            view.form_valid(form)

            # Assert
            form.save.assert_called_once_with(commit=False)
            self.assertEqual(mock_signup.recruitment, mock_object)
            mock_signup.save.assert_called_once()
            mock_super().form_valid.assert_called_once_with(form)

    def test_get(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        mock_object = mock.MagicMock()
        view = InstructorRecruitmentAddSignup(request=request, kwargs={"pk": 11200})
        view.get_object = mock.MagicMock(return_value=mock_object)

        # Act
        with mock.patch("recruitment.views.super") as mock_super:
            view.get(request)

            # Assert
            self.assertEqual(view.request, request)
            self.assertEqual(view.object, mock_object)
            mock_super().get.assert_called_once_with(request)

    def test_post(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        mock_object = mock.MagicMock()
        view = InstructorRecruitmentAddSignup(request=request, kwargs={"pk": 11200})
        view.get_object = mock.MagicMock(return_value=mock_object)

        # Act
        with mock.patch("recruitment.views.super") as mock_super:
            view.post(request)

            # Assert
            self.assertEqual(view.request, request)
            self.assertEqual(view.object, mock_object)
            mock_super().post.assert_called_once_with(request)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        recruitment = InstructorRecruitment.objects.create(
            event=event, notes="Test notes"
        )
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        config = CommunityRoleConfig.objects.create(
            name="instructor",
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        inactivation = CommunityRoleInactivation.objects.create(name="inactivation")
        CommunityRole.objects.create(
            config=config,
            person=person,
            inactivation=inactivation,
        )
        notes = "Lorem ipsum"
        data = {"person": person.pk, "notes": notes}
        url = reverse("instructorrecruitment_add_signup", args=[recruitment.pk])
        success_url = reverse("all_instructorrecruitment")
        # Act
        response = self.client.post(url, data, follow=False)
        # Assert
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, success_url)
        self.assertEqual(recruitment.signups.count(), 1)
        signup = recruitment.signups.last()
        self.assertEqual(signup.person, person)
        self.assertEqual(signup.user_notes, "")
        self.assertEqual(signup.notes, notes)


class TestInstructorRecruitmentSignupChangeState(FakeRedisTestCaseMixin, TestBase):
    def setUp(self):
        super().setUp()

        # save scheduler and connection data
        self._saved_scheduler = recruitment.views.scheduler
        self._saved_redis_connection = recruitment.views.redis_connection
        # overwrite them
        recruitment.views.scheduler = self.scheduler
        recruitment.views.redis_connection = self.connection

    def tearDown(self):
        super().tearDown()
        recruitment.views.scheduler = self._saved_scheduler
        recruitment.views.redis_connection = self._saved_redis_connection

    def _prepare_email_automation_data(self) -> None:
        self.automated_email_tag = Tag.objects.create(
            name="automated-email", priority=0
        )
        template = EmailTemplate.objects.create(
            slug="sample-template",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(action="new-instructor", template=template)

    def test_class_fields(self) -> None:
        # Arrange
        view = InstructorRecruitmentSignupChangeState()
        # Assert
        self.assertEqual(
            view.permission_required, "recruitment.change_instructorrecruitmentsignup"
        )
        self.assertEqual(view.form_class, InstructorRecruitmentSignupChangeStateForm)

    def test_get_object(self) -> None:
        # Arrange
        pk = 120000
        view = InstructorRecruitmentSignupChangeState(kwargs={"pk": pk})
        # Act
        with mock.patch("recruitment.views.InstructorRecruitmentSignup") as mock_signup:
            view.get_object()
        # Assert
        mock_signup.objects.get.assert_called_once_with(pk=pk)

    def test_get_success_url(self) -> None:
        # Arrange
        url_redirect = {
            "/asdasd": "/asdasd",
            "/asdasd?status=o": "/asdasd?status=o",
            "https://google.com/": reverse("all_instructorrecruitment"),
            None: reverse("all_instructorrecruitment"),
        }
        for url, redirect in url_redirect.items():
            request = RequestFactory().post("/", {"next": url} if url else {})
            pk = 120000
            view = InstructorRecruitmentSignupChangeState(kwargs={"pk": pk})
            with mock.patch("recruitment.views.InstructorRecruitmentSignup"):
                view.post(request)
            # Act
            result = view.get_success_url()
            # Assert
            self.assertEqual(result, redirect)

    def test_form_invalid__redirects_to_success_url(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        pk = 120000
        view = InstructorRecruitmentSignupChangeState(kwargs={"pk": pk})
        with mock.patch("recruitment.views.InstructorRecruitmentSignup"):
            view.post(request)
        # Act
        with mock.patch.object(
            InstructorRecruitmentSignupChangeState, "get_success_url"
        ) as mock_get_success_url:
            mock_get_success_url.return_value = "/"
            result = view.form_invalid(mock.MagicMock())
        # Assert
        mock_get_success_url.assert_called_once()
        self.assertEqual(result.status_code, 302)

    def test_form_valid(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        mock_object = mock.MagicMock()
        view = InstructorRecruitmentSignupChangeState(
            object=mock_object, request=request
        )
        view.add_instructor_task = mock.MagicMock()
        view.remove_instructor_task = mock.MagicMock()
        data = {"action": "confirm"}
        form = InstructorRecruitmentSignupChangeStateForm(data)
        form.is_valid()
        # Act
        view.form_valid(form)
        # Assert
        self.assertEqual(mock_object.state, "a")
        mock_object.save.assert_called_once()
        view.add_instructor_task.assert_called_once_with(
            mock_object.person, mock_object.recruitment.event
        )
        view.remove_instructor_task.assert_not_called()

    def test_add_instructor_task(self) -> None:
        # Arrange
        super()._setUpRoles()
        self._prepare_email_automation_data()
        request = RequestFactory().post("/")
        view = InstructorRecruitmentSignupChangeState(request=request)
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        organization = self.org_alpha
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        event.tags.add(self.automated_email_tag)
        # Act
        task = view.add_instructor_task(person, event)
        # Assert
        self.assertTrue(task.pk)
        self.assertTrue(NewInstructorAction.check(task))
        self.assertTrue(task.rq_jobs.all())

        # 1 new jobs
        self.assertEqual(self.scheduler.count(), 1)
        job = next(self.scheduler.get_jobs())
        # 1 new rqjobs
        self.assertEqual(RQJob.objects.count(), 1)
        rqjob = RQJob.objects.first()
        # ensure it's the same job
        self.assertEqual(job.get_id(), rqjob.job_id)

    def test_remove_instructor_task(self) -> None:
        # Arrange
        super()._setUpRoles()
        self._prepare_email_automation_data()
        request = RequestFactory().post("/")
        view = InstructorRecruitmentSignupChangeState(request=request)
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        role = Role.objects.get(name="instructor")
        task = Task.objects.create(person=person, event=event, role=role)
        # Act
        view.remove_instructor_task(person, event)
        # Assert
        with self.assertRaises(Task.DoesNotExist):
            task.refresh_from_db()

    def test_remove_instructor_task__no_task(self) -> None:
        # Arrange
        super()._setUpRoles()
        self._prepare_email_automation_data()
        request = RequestFactory().post("/")
        view = InstructorRecruitmentSignupChangeState(request=request)
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        # Act & Assert - no error
        view.remove_instructor_task(person, event)

    def test_post__form_valid(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        view = InstructorRecruitmentSignupChangeState()
        # Act
        # TODO: switch syntax for multiple context managers in Python 3.10+
        # https://docs.python.org/3.10/whatsnew/3.10.html#parenthesized-context-managers
        with mock.patch.object(
            InstructorRecruitmentSignupChangeState, "get_object"
        ) as mock_get_object, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "get_form"
        ) as mock_get_form, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "form_valid"
        ) as mock_form_valid, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "form_invalid"
        ) as mock_form_invalid:
            mock_get_form.return_value.is_valid.return_value = True
            view.post(request)
        # Assert
        mock_get_object.assert_called_once()
        mock_get_form.assert_called_once()
        mock_get_form.return_value.is_valid.assert_called_once()
        mock_form_valid.assert_called_once_with(mock_get_form.return_value)
        mock_form_invalid.assert_not_called()

    def test_post__form_invalid(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        view = InstructorRecruitmentSignupChangeState()
        # Act
        # TODO: switch syntax for multiple context managers in Python 3.10+
        # https://docs.python.org/3.10/whatsnew/3.10.html#parenthesized-context-managers
        with mock.patch.object(
            InstructorRecruitmentSignupChangeState, "get_object"
        ) as mock_get_object, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "get_form"
        ) as mock_get_form, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "form_valid"
        ) as mock_form_valid, mock.patch.object(
            InstructorRecruitmentSignupChangeState, "form_invalid"
        ) as mock_form_invalid:
            mock_get_form.return_value.is_valid.return_value = False
            view.post(request)
        # Assert
        mock_get_object.assert_called_once()
        mock_get_form.assert_called_once()
        mock_get_form.return_value.is_valid.assert_called_once()
        mock_form_valid.assert_not_called()
        mock_form_invalid.assert_called_once_with(mock_get_form.return_value)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        recruitment = InstructorRecruitment.objects.create(
            event=event, notes="Test notes"
        )
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        signup = InstructorRecruitmentSignup.objects.create(
            recruitment=recruitment, person=person
        )
        role = Role.objects.create(name="instructor")
        data = {"action": "confirm"}
        url = reverse("instructorrecruitmentsignup_changestate", args=[signup.pk])
        success_url = reverse("all_instructorrecruitment")
        # Act
        response = self.client.post(url, data, follow=False)
        signup.refresh_from_db()
        # Assert
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, success_url)
        self.assertEqual(signup.state, "a")
        self.assertTrue(Task.objects.get(event=event, person=person, role=role))


class TestInstructorRecruitmentChangeState(FakeRedisTestCaseMixin, TestBase):
    def setUp(self):
        super().setUp()

        # save scheduler and connection data
        self._saved_scheduler = recruitment.views.scheduler
        self._saved_redis_connection = recruitment.views.redis_connection
        # overwrite them
        recruitment.views.scheduler = self.scheduler
        recruitment.views.redis_connection = self.connection

    def tearDown(self):
        super().tearDown()
        recruitment.views.scheduler = self._saved_scheduler
        recruitment.views.redis_connection = self._saved_redis_connection

    def _prepare_event_and_recruitment(self) -> None:
        Tag.objects.bulk_create(
            [
                Tag(name="automated-email", priority=0),
                Tag(name="LC", priority=30),
            ]
        )
        Organization.objects.bulk_create(
            [Organization(domain="carpentries.org", fullname="Instructor Training")]
        )
        self.event = Event.objects.create(
            slug="test-event",
            host=Organization.objects.first(),
            administrator=Organization.objects.get(domain="carpentries.org"),
            start=date.today() + timedelta(days=7),
            end=date.today() + timedelta(days=8),
        )
        self.event.tags.set(Tag.objects.filter(name__in=["LC", "automated-email"]))
        self.recruitment = InstructorRecruitment.objects.create(
            event=self.event, status="c"
        )

    def _prepare_email_automation_data(self) -> None:
        self._prepare_event_and_recruitment()
        instructor_role = Role.objects.create(name="instructor")
        host_role = Role.objects.create(name="host")
        person1 = Person.objects.create(
            username="test1", personal="Test1", family="Test", email="test1@example.org"
        )
        person2 = Person.objects.create(
            username="test2", personal="Test2", family="Test", email="test2@example.org"
        )
        person3 = Person.objects.create(
            username="test3", personal="Test3", family="Test", email="test3@example.org"
        )
        Task.objects.bulk_create(
            [
                Task(person=person1, role=host_role, event=self.event),
                Task(person=person2, role=instructor_role, event=self.event),
                Task(person=person3, role=instructor_role, event=self.event),
            ]
        )
        InstructorRecruitmentSignup.objects.create(
            person=person2,
            recruitment=self.recruitment,
            state="a",
        )
        self.signup2 = InstructorRecruitmentSignup.objects.create(
            person=person3,
            recruitment=self.recruitment,
            state="d",
        )

        template1 = EmailTemplate.objects.create(
            slug="sample-template1",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(
            action=DeclinedInstructorsAction.trigger_name, template=template1
        )

        template2 = EmailTemplate.objects.create(
            slug="sample-template2",
            subject="Welcome!",
            to_header="",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="",
            body_template="# Welcome",
        )
        Trigger.objects.create(
            action="instructors-host-introduction", template=template2
        )

    def test_class_fields(self) -> None:
        # Arrange
        view = InstructorRecruitmentChangeState()
        # Assert
        self.assertEqual(
            view.permission_required, "recruitment.change_instructorrecruitment"
        )

    def test_get_object(self) -> None:
        # Arrange
        pk = 120000
        view = InstructorRecruitmentChangeState(kwargs={"pk": pk})
        # Act
        with mock.patch("recruitment.views.InstructorRecruitment") as mock_recruitment:
            view.get_object()
        # Assert
        mock_recruitment.objects.annotate().get.assert_called_once_with(pk=pk)

    def test_get_success_url(self) -> None:
        # Arrange
        url_redirect = {
            "/asdasd": "/asdasd",
            "/asdasd?status=o": "/asdasd?status=o",
            "https://google.com/": reverse("all_instructorrecruitment"),
            None: reverse("all_instructorrecruitment"),
        }
        for url, redirect in url_redirect.items():
            request = RequestFactory().post("/", {"next": url} if url else {})
            view = InstructorRecruitmentChangeState(request=request)
            # Act
            result = view.get_success_url()
            # Assert
            self.assertEqual(result, redirect)

    def test_post__action_close(self) -> None:
        # Arrange
        request = RequestFactory().post("/", data={"action": "close"})
        mock_object = mock.MagicMock()
        view = InstructorRecruitmentChangeState(request=request, kwargs={"pk": 11200})
        view.get_object = mock.MagicMock(return_value=mock_object)
        view.close_recruitment = mock.MagicMock()
        view.reopen_recruitment = mock.MagicMock()

        # Act
        view.post(request)

        # Assert
        self.assertEqual(view.request, request)
        self.assertEqual(view.object, mock_object)
        view.close_recruitment.assert_called_once_with()
        view.reopen_recruitment.assert_not_called()

    def test_post__action_reopen(self) -> None:
        # Arrange
        request = RequestFactory().post("/", data={"action": "reopen"})
        mock_object = mock.MagicMock()
        view = InstructorRecruitmentChangeState(request=request, kwargs={"pk": 11200})
        view.get_object = mock.MagicMock(return_value=mock_object)
        view.close_recruitment = mock.MagicMock()
        view.reopen_recruitment = mock.MagicMock()

        # Act
        view.post(request)

        # Assert
        self.assertEqual(view.request, request)
        self.assertEqual(view.object, mock_object)
        view.close_recruitment.assert_not_called()
        view.reopen_recruitment.assert_called_once_with()

    def test__validate_for_closing(self) -> None:
        # Arrange
        recruitment1 = InstructorRecruitment(event=None, status="o")
        recruitment1.num_pending = 123
        recruitment2 = InstructorRecruitment(event=None, status="c")
        recruitment2.num_pending = 123
        recruitment3 = InstructorRecruitment(event=None, status="o")
        recruitment3.num_pending = 0
        recruitment4 = InstructorRecruitment(event=None, status="c")
        recruitment4.num_pending = 0
        data = [
            (recruitment1, False),
            (recruitment2, False),
            (recruitment3, True),
            (recruitment4, False),
            (InstructorRecruitment(event=None, status="o"), False),
            (InstructorRecruitment(event=None, status="c"), False),
        ]
        for R, expected in data:
            # Act
            result = InstructorRecruitmentChangeState._validate_for_closing(R)
            # Assert
            self.assertEqual(result, expected)

    def test_close_recruitment__failure(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        view = InstructorRecruitmentChangeState(request=request)
        view._validate_for_closing = mock.MagicMock(return_value=False)
        view.object = mock.MagicMock()
        view.get_success_url = mock.MagicMock(return_value="")

        # Act
        with mock.patch("recruitment.views.messages") as mock_messages:
            result = view.close_recruitment()

        # Assert
        mock_messages.success.assert_not_called()
        mock_messages.error.assert_called_once_with(
            request, "Unable to close recruitment."
        )
        self.assertEqual(result.status_code, 302)

    def test_close_recruitment__success(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        view = InstructorRecruitmentChangeState(request=request)
        view._validate_for_closing = mock.MagicMock(return_value=True)
        view.object = mock.MagicMock()
        view.send_introduction_email = mock.MagicMock()
        view.send_thank_you_to_declined = mock.MagicMock()
        view.get_success_url = mock.MagicMock(return_value="")

        # Act
        with mock.patch("recruitment.views.messages") as mock_messages:
            result = view.close_recruitment()

        # Assert
        self.assertEqual(view.object.status, "c")
        view.object.save.assert_called_once_with()
        mock_messages.success.assert_called_once_with(
            request, f"Successfully closed recruitment {view.object}."
        )
        view.send_introduction_email.assert_called_once_with(
            view.object.event, view.object
        )
        view.send_thank_you_to_declined.assert_called_once_with(view.object)
        view.get_success_url.assert_called_once_with()
        self.assertEqual(result.status_code, 302)

    def test_send_introduction_email__failure(self) -> None:
        # Arrange
        self._prepare_email_automation_data()
        self.recruitment.status = "o"
        self.recruitment.save()

        request = RequestFactory().post("/")
        view = InstructorRecruitmentChangeState(request=request)

        # Act
        with mock.patch("recruitment.views.messages") as mock_messages, mock.patch(
            "recruitment.views.ActionManageMixin"
        ) as mock_action_manage:
            view.send_introduction_email(self.event, self.recruitment)

        # Assert
        mock_messages.warning.assert_called_once_with(
            request,
            "Instructors-Host introduction email was not sent due to unmet conditions.",
        )
        mock_action_manage.add.assert_not_called()

    def test_send_introduction_email__success(self) -> None:
        # Arrange
        self._prepare_email_automation_data()
        request = RequestFactory().post("/")
        view = InstructorRecruitmentChangeState(request=request)

        # Act
        with mock.patch("recruitment.views.messages") as mock_messages, mock.patch(
            "recruitment.views.ActionManageMixin"
        ) as mock_action_manage:
            view.send_introduction_email(self.event, self.recruitment)

        # Assert
        mock_messages.warning.assert_not_called()
        mock_action_manage.add.assert_called_once_with(
            action_class=InstructorsHostIntroductionAction,
            logger=recruitment.views.logger,
            scheduler=self.scheduler,
            triggers=mock.ANY,
            context_objects=dict(event=self.event, recruitment=self.recruitment),
            object_=self.event,
            request=view.request,
        )

    def test_send_thank_you_to_declined(self) -> None:
        # Arrange
        self._prepare_email_automation_data()
        request = RequestFactory().post("/")
        view = InstructorRecruitmentChangeState(request=request)

        # Act
        with mock.patch("recruitment.views.ActionManageMixin") as mock_action_manage:
            view.send_thank_you_to_declined(self.recruitment)

        # Assert
        mock_action_manage.add.assert_called_once_with(
            action_class=DeclinedInstructorsAction,
            logger=recruitment.views.logger,
            scheduler=self.scheduler,
            triggers=mock.ANY,
            context_objects=dict(
                recruitment=self.recruitment,
                event=self.event,
                person=self.signup2.person,
            ),
            object_=self.signup2,
            request=view.request,
        )

    def test__validate_for_reopening(self) -> None:
        # Arrange
        recruitment1 = InstructorRecruitment(event=None, status="o")
        recruitment2 = InstructorRecruitment(event=None, status="c")
        data = [
            (recruitment1, False),
            (recruitment2, True),
            (InstructorRecruitment(event=None, status="o"), False),
            (InstructorRecruitment(event=None, status="c"), True),
        ]
        for R, expected in data:
            # Act
            result = InstructorRecruitmentChangeState._validate_for_reopening(R)
            # Assert
            self.assertEqual(result, expected)

    def test_reopen_recruitment__failure(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        view = InstructorRecruitmentChangeState(request=request)
        view._validate_for_reopening = mock.MagicMock(return_value=False)
        view.object = mock.MagicMock()
        view.get_success_url = mock.MagicMock(return_value="")

        # Act
        with mock.patch("recruitment.views.messages") as mock_messages:
            result = view.reopen_recruitment()

        # Assert
        mock_messages.success.assert_not_called()
        mock_messages.error.assert_called_once_with(
            request, "Unable to re-open recruitment."
        )
        self.assertEqual(result.status_code, 302)

    def test_reopen_recruitment__success(self) -> None:
        # Arrange
        request = RequestFactory().post("/")
        view = InstructorRecruitmentChangeState(request=request)
        view._validate_for_reopening = mock.MagicMock(return_value=True)
        view.object = mock.MagicMock()
        view.get_success_url = mock.MagicMock(return_value="")

        # Act
        with mock.patch("recruitment.views.messages") as mock_messages:
            result = view.reopen_recruitment()

        # Assert
        self.assertEqual(view.object.status, "o")
        view.object.save.assert_called_once_with()
        mock_messages.success.assert_called_once_with(
            request, f"Successfully re-opened recruitment {view.object}."
        )
        view.get_success_url.assert_called_once_with()
        self.assertEqual(result.status_code, 302)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration__action_close(self) -> None:
        # Arrange
        self._prepare_email_automation_data()
        self.recruitment.status = "o"
        self.recruitment.save()

        super()._setUpUsersAndLogin()
        url = reverse("instructorrecruitment_changestate", args=[self.recruitment.pk])
        success_url = reverse("all_instructorrecruitment")

        # Act
        response = self.client.post(url, {"action": "close"}, follow=False)
        self.recruitment.refresh_from_db()

        # Assert
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, success_url)
        self.assertEqual(self.recruitment.status, "c")
        self.assertTrue(
            self.event.rq_jobs.get(trigger__action="instructors-host-introduction")
        )
        self.assertTrue(
            RQJob.objects.get(trigger__action=DeclinedInstructorsAction.trigger_name)
        )

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration__action_reopen(self) -> None:
        # Arrange
        self._prepare_event_and_recruitment()
        self.recruitment.status = "c"
        self.recruitment.save()

        super()._setUpUsersAndLogin()
        url = reverse("instructorrecruitment_changestate", args=[self.recruitment.pk])
        success_url = reverse("all_instructorrecruitment")

        # Act
        response = self.client.post(url, {"action": "reopen"}, follow=False)
        self.recruitment.refresh_from_db()

        # Assert
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, success_url)
        self.assertEqual(self.recruitment.status, "o")


class TestInstructorRecruitmentSignupUpdateView(TestBase):
    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_integration(self) -> None:
        # Arrange
        super()._setUpUsersAndLogin()
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        recruitment = InstructorRecruitment.objects.create(
            event=event, notes="Test notes"
        )
        person = Person.objects.create(
            personal="Test", family="User", username="test_user"
        )
        signup = InstructorRecruitmentSignup.objects.create(
            recruitment=recruitment, person=person, notes="Admin notes to be changed"
        )
        data = {"notes": "New admin notes"}
        url = reverse("instructorrecruitmentsignup_edit", args=[signup.pk])
        success_url = reverse("all_instructorrecruitment")
        # Act
        response = self.client.post(url, data, follow=False)
        signup.refresh_from_db()
        # Assert
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, success_url)
        self.assertEqual(signup.notes, "New admin notes")
