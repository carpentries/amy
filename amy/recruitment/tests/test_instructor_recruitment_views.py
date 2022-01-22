from datetime import date
from unittest import mock

from django.test import override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from recruitment.filters import InstructorRecruitmentFilter
from recruitment.forms import InstructorRecruitmentCreateForm
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from recruitment.views import (
    InstructorRecruitmentCreate,
    InstructorRecruitmentDetails,
    InstructorRecruitmentList,
)
from workshops.models import Event, Language, Organization, Person, WorkshopRequest
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
            list(
                response.context["object_list"][0].instructorrecruitmentsignup_set.all()
            ),
            [signup],
        )


class TestInstructorRecruitmentCreateView(TestBase):
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
        self.assertEqual(view.event, None)

    def test_get_other_object(self) -> None:
        # Arrange
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        view = InstructorRecruitmentCreate(kwargs={"event_id": event.pk})
        # Act
        object = view.get_other_object()
        # Assert
        self.assertEqual(event, object)

    def test_get(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
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
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
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
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
        view = InstructorRecruitmentCreate(request=request)
        view.event = event
        # Act
        kwargs = view.get_form_kwargs()
        # Assert
        self.assertEqual(kwargs, {"initial": {}, "prefix": "instructorrecruitment"})

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
                "event_dates": "Dec 29, 2021-???",
                "view": view,
                "model": InstructorRecruitment,
                # it needs to be the same instance, otherwise the test fails
                "form": context["form"],
            },
        )

    def test_get_initial(self) -> None:
        # Arrange
        request = RequestFactory().get("/")
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
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
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
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
        organization = Organization.objects.first()
        event = Event.objects.create(
            slug="test-event",
            host=organization,
            administrator=organization,
        )
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
