from datetime import date
from unittest.mock import MagicMock, call, patch

from django.contrib.messages.api import MessageFailure
from django.test import TestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from communityroles.models import (
    CommunityRole,
    CommunityRoleConfig,
    CommunityRoleInactivation,
)
from dashboard.views import (
    ResignFromRecruitment,
    SignupForRecruitment,
    UpcomingTeachingOpportunitiesList,
)
from recruitment.models import InstructorRecruitment, InstructorRecruitmentSignup
from workshops.models import Event, Organization, Person, Role, Task


class TestUpcomingTeachingOpportunitiesList(TestCase):
    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_view_enabled__no_community_role(self):
        # Arrange
        request = RequestFactory().get("/")
        request.user = Person(personal="Test", family="User", email="test@user.com")
        # Act
        view = UpcomingTeachingOpportunitiesList(request=request)
        # Assert
        self.assertEqual(view.get_view_enabled(), False)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_view_enabled__community_role_inactive(self):
        # Arrange
        request = RequestFactory().get("/")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        request.user = person
        config = CommunityRoleConfig.objects.create(
            name="instructor",
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        inactivation = CommunityRoleInactivation.objects.create(name="inactivation")
        role = CommunityRole.objects.create(
            config=config,
            person=person,
            inactivation=inactivation,
        )
        # Act
        view = UpcomingTeachingOpportunitiesList(request=request)
        # Assert
        self.assertEqual(role.is_active(), False)
        self.assertEqual(view.get_view_enabled(), False)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_view_enabled__community_role_active(self):
        # Arrange
        request = RequestFactory().get("/")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        request.user = person
        config = CommunityRoleConfig.objects.create(
            name="instructor",
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        role = CommunityRole.objects.create(
            config=config,
            person=person,
        )
        # Act
        view = UpcomingTeachingOpportunitiesList(request=request)
        # Assert
        self.assertEqual(role.is_active(), True)
        self.assertEqual(view.get_view_enabled(), True)

    def test_get_queryset(self):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        event = Event.objects.create(slug="test-event", host=host)
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)
        signup = InstructorRecruitmentSignup.objects.create(
            recruitment=recruitment, person=person, interest="session"
        )
        request = RequestFactory().get("/")
        request.user = person
        # Act
        view = UpcomingTeachingOpportunitiesList(request=request)
        qs = view.get_queryset()
        # Assert
        self.assertEqual(list(qs), [recruitment])
        # `person_signup` is an additional attribute created using `Prefetch()`
        self.assertEqual(list(qs[0].person_signup), [signup])

    def test_get_context_data(self):
        """Context data is extended only with person object, but it includes pre-counted
        number of roles.

        This is heavy test: a lot of data needs to be created in order to run
        `get_context_data` in the view."""
        # Arrange
        request = RequestFactory().get("/")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        instructor = Role.objects.create(name="instructor")
        supporting_instructor = Role.objects.create(name="supporting-instructor")
        helper = Role.objects.create(name="helper")
        host = Organization.objects.first()
        event1 = Event.objects.create(slug="test-event1", host=host)
        event2 = Event.objects.create(slug="test-event2", host=host)
        event3 = Event.objects.create(slug="test-event3", host=host)
        Task.objects.create(role=instructor, person=person, event=event1)
        Task.objects.create(role=supporting_instructor, person=person, event=event1)
        Task.objects.create(role=supporting_instructor, person=person, event=event2)
        Task.objects.create(role=helper, person=person, event=event1)
        Task.objects.create(role=helper, person=person, event=event2)
        Task.objects.create(role=helper, person=person, event=event3)
        signup1 = InstructorRecruitmentSignup.objects.create(
            person=person,
            recruitment=InstructorRecruitment.objects.create(event=event3),
        )
        request.user = person
        view = UpcomingTeachingOpportunitiesList(request=request)
        view.get_queryset()
        # Act & Assert
        with self.assertNumQueries(2):
            data = view.get_context_data(object_list=[])
        # Assert
        self.assertEqual(data["person"].num_taught, 1)
        self.assertEqual(data["person"].num_supporting, 2)
        self.assertEqual(data["person"].num_helper, 3)
        self.assertEqual(list(data["person_instructor_tasks_slugs"]), [event1.slug])
        self.assertEqual(data["person_instructor_task_events"], {event1})
        self.assertEqual(list(data["person_signups"]), [signup1])


class TestSignupForRecruitment(TestCase):
    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_view_enabled__no_community_role(self):
        # Arrange
        request = RequestFactory().get("/")
        request.user = Person(personal="Test", family="User", email="test@user.com")
        # Act
        view = SignupForRecruitment(request=request)
        # Assert
        self.assertEqual(view.get_view_enabled(), False)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_view_enabled__community_role_inactive(self):
        # Arrange
        request = RequestFactory().get("/")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        request.user = person
        config = CommunityRoleConfig.objects.create(
            name="instructor",
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        inactivation = CommunityRoleInactivation.objects.create(name="inactivation")
        role = CommunityRole.objects.create(
            config=config,
            person=person,
            inactivation=inactivation,
        )
        # Act
        view = SignupForRecruitment(request=request)
        # Assert
        self.assertEqual(role.is_active(), False)
        self.assertEqual(view.get_view_enabled(), False)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_view_enabled__community_role_active(self):
        # Arrange
        request = RequestFactory().get("/")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        request.user = person
        config = CommunityRoleConfig.objects.create(
            name="instructor",
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        role = CommunityRole.objects.create(
            config=config,
            person=person,
        )
        # Act
        view = SignupForRecruitment(request=request)
        # Assert
        self.assertEqual(role.is_active(), True)
        self.assertEqual(view.get_view_enabled(), True)

    def test_get_context_data(self):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        event = Event.objects.create(
            slug="test-event", host=host, start=date(2022, 2, 19), end=date(2022, 2, 20)
        )
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        instructor_role = Role.objects.create(name="instructor")
        Task.objects.create(event=event, person=person, role=instructor_role)
        request = RequestFactory().get("/")
        request.user = person
        view = SignupForRecruitment(
            request=request, object=None, kwargs={"recruitment_pk": recruitment.pk}
        )
        view.other_object = view.get_other_object()
        # Act & Assert
        with self.assertNumQueries(1):
            data = view.get_context_data()
        # Assert
        self.assertEqual(data["title"], f"Signup for workshop {event}")
        # `num_*` are special fields added through `QuerySet.annotate`
        self.assertEqual(data["person"].num_taught, 1)
        self.assertEqual(data["person"].num_supporting, 0)
        self.assertEqual(data["person"].num_helper, 0)

    def test_get_success_message(self):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        event = Event.objects.create(
            slug="test-event", host=host, start=date(2022, 2, 19), end=date(2022, 2, 20)
        )
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        request = RequestFactory().get("/")
        request.user = person
        view = SignupForRecruitment(
            request=request, kwargs={"recruitment_pk": recruitment.pk}
        )
        view.other_object = view.get_other_object()
        # Act
        msg = view.get_success_message(None)
        # Assert
        self.assertEqual(
            msg,
            f"Your interest in teaching at {event} has been recorded and is now "
            "pending.",
        )

    def test_get_success_url__no_next_param(self):
        # Arrange
        request = RequestFactory().get("/")
        view = SignupForRecruitment(request=request)
        # Act
        url = view.get_success_url()
        # Assert
        self.assertEqual(url, reverse("upcoming-teaching-opportunities"))

    def test_get_success_url__with_next_param(self):
        # Arrange
        next_url = "/dashboard"
        request = RequestFactory().get(f"/?next={next_url}")
        view = SignupForRecruitment(request=request)
        # Act
        url = view.get_success_url()
        # Assert
        self.assertEqual(url, next_url)

    def test_get_form_kwargs(self):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        event = Event.objects.create(
            slug="test-event", host=host, start=date(2022, 2, 19), end=date(2022, 2, 20)
        )
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)
        request = RequestFactory().get("/")
        request.user = MagicMock()
        view = SignupForRecruitment(
            request=request, kwargs={"recruitment_pk": recruitment.pk}
        )
        view.other_object = view.get_other_object()
        # Act
        kwargs = view.get_form_kwargs()
        # Assert
        self.assertEqual(
            kwargs,
            {
                "initial": {},
                "person": request.user,
                "recruitment": recruitment,
                "prefix": None,
            },
        )

    def test_form_valid__obj_saved_with_recruitment_and_person(self):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        event = Event.objects.create(
            slug="test-event", host=host, start=date(2022, 2, 19), end=date(2022, 2, 20)
        )
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)
        request = RequestFactory().get("/")
        request.user = person
        view = SignupForRecruitment(
            request=request, kwargs={"recruitment_pk": recruitment.pk}
        )
        view.other_object = view.get_other_object()
        form_mock = MagicMock()
        # Act
        with self.assertRaises(MessageFailure):
            # MessageFailure is expected here, it happens after the form saving part
            view.form_valid(form_mock)
        # Assert
        form_mock.save.has_calls(call(commit=False))
        form_mock.save().save.assert_called_once_with()
        self.assertEqual(form_mock.save().recruitment, recruitment)
        self.assertEqual(form_mock.save().person, person)

    @patch("dashboard.views.messages")
    def test_form_valid__tasks_nearby(self, mock_messages):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        event = Event.objects.create(
            slug="test-event", host=host, start=date(2022, 2, 19), end=date(2022, 2, 20)
        )
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)

        event2 = Event.objects.create(
            slug="test2-event",
            host=host,
            start=date(2022, 2, 4),  # dates are overlapping +- 14 days with test-event
            end=date(2022, 2, 5),
        )
        instructor_role = Role.objects.create(name="instructor")
        Task.objects.create(event=event2, person=person, role=instructor_role)
        request = RequestFactory().get("/")
        request.user = person
        view = SignupForRecruitment(
            request=request, kwargs={"recruitment_pk": recruitment.pk}
        )
        view.other_object = view.get_other_object()

        # Act
        with self.assertRaises(AttributeError):
            # AttributeError is expected here, it happens after checking tasks nearby
            view.form_valid(view.get_form())

        # Assert
        mock_messages.warning.assert_called_once_with(
            request,
            "Selected event dates fall within 14 days of your other workshops: "
            f"{event2}",
        )

    @patch("dashboard.views.messages")
    def test_form_valid__conflicting_signups(self, mock_messages):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        event = Event.objects.create(
            slug="test-event", host=host, start=date(2022, 2, 19), end=date(2022, 2, 20)
        )
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)

        event2 = Event.objects.create(
            slug="test-event2",
            host=host,
            start=date(2022, 2, 18),  # dates are overlapping with test-event
            end=date(2022, 2, 19),
        )
        recruitment2 = InstructorRecruitment.objects.create(status="o", event=event2)
        signup = InstructorRecruitmentSignup.objects.create(
            person=person, recruitment=recruitment2
        )

        request = RequestFactory().get("/")
        request.user = person
        view = SignupForRecruitment(
            request=request, kwargs={"recruitment_pk": recruitment.pk}
        )
        view.other_object = view.get_other_object()

        # Act
        with self.assertRaises(AttributeError):
            # AttributeError is expected here, it happens after checking tasks nearby
            view.form_valid(view.get_form())

        # Assert
        mock_messages.warning.assert_called_once_with(
            request,
            "You have applied to other workshops on the same dates: "
            f"{signup.recruitment.event}",
        )

    @patch("django.contrib.messages.views.messages")
    def test_form_valid__creates_a_new_signup(self, mock_contrib_messages_views):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        event = Event.objects.create(
            slug="test-event", host=host, start=date(2022, 2, 19), end=date(2022, 2, 20)
        )
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)

        request = RequestFactory().post("/")
        request.user = person
        view = SignupForRecruitment(
            request=request, kwargs={"recruitment_pk": recruitment.pk}
        )
        view.other_object = view.get_other_object()

        # Act
        form = view.get_form()
        form.is_valid()
        view.form_valid(form)

        # Assert
        mock_contrib_messages_views.success.assert_called_once_with(
            request, view.get_success_message(None)
        )
        # new object created
        self.assertTrue(isinstance(view.object, InstructorRecruitmentSignup))


class TestResignFromRecruitment(TestCase):
    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_view_enabled__no_community_role(self):
        # Arrange
        request = RequestFactory().post("/")
        request.user = Person(personal="Test", family="User", email="test@user.com")
        # Act
        view = ResignFromRecruitment(request=request)
        # Assert
        self.assertEqual(view.get_view_enabled(), False)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_view_enabled__community_role_inactive(self):
        # Arrange
        request = RequestFactory().post("/")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        request.user = person
        config = CommunityRoleConfig.objects.create(
            name="instructor",
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        inactivation = CommunityRoleInactivation.objects.create(name="inactivation")
        role = CommunityRole.objects.create(
            config=config,
            person=person,
            inactivation=inactivation,
        )
        # Act
        view = ResignFromRecruitment(request=request)
        # Assert
        self.assertEqual(role.is_active(), False)
        self.assertEqual(view.get_view_enabled(), False)

    @override_settings(INSTRUCTOR_RECRUITMENT_ENABLED=True)
    def test_view_enabled__community_role_active(self):
        # Arrange
        request = RequestFactory().post("/")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        request.user = person
        config = CommunityRoleConfig.objects.create(
            name="instructor",
            display_name="Instructor",
            link_to_award=False,
            link_to_membership=False,
            additional_url=False,
        )
        role = CommunityRole.objects.create(
            config=config,
            person=person,
        )
        # Act
        view = ResignFromRecruitment(request=request)
        # Assert
        self.assertEqual(role.is_active(), True)
        self.assertEqual(view.get_view_enabled(), True)

    def test_get_queryset(self):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person1 = Person.objects.create(
            personal="Test1", family="User1", email="test1@user1.com", username="test1"
        )
        person2 = Person.objects.create(
            personal="Test2", family="User2", email="test2@user2.com", username="test2"
        )
        event1 = Event.objects.create(slug="test-event1", host=host)
        event2 = Event.objects.create(slug="test-event2", host=host)
        recruitment1 = InstructorRecruitment.objects.create(status="c", event=event1)
        recruitment2 = InstructorRecruitment.objects.create(status="o", event=event2)
        signup1 = InstructorRecruitmentSignup(recruitment=recruitment1, person=person1)
        signup2 = InstructorRecruitmentSignup(recruitment=recruitment1, person=person2)
        signup3 = InstructorRecruitmentSignup(recruitment=recruitment2, person=person1)
        signup4 = InstructorRecruitmentSignup(recruitment=recruitment2, person=person2)
        InstructorRecruitmentSignup.objects.bulk_create(
            [signup1, signup2, signup3, signup4]
        )

        request = RequestFactory().post("/")
        request.user = person1
        view = ResignFromRecruitment(request=request)

        # Act
        signups = view.get_queryset()

        # Assert
        self.assertEqual(list(signups), [signup3])

    def test_get_redirect_url__no_next_param(self):
        # Arrange
        request = RequestFactory().post("/")
        view = ResignFromRecruitment(request=request)
        # Act
        url = view.get_redirect_url()
        # Assert
        self.assertEqual(url, reverse("upcoming-teaching-opportunities"))

    def test_get_redirect_url__with_next_param(self):
        # Arrange
        next_url = "/dashboard"
        request = RequestFactory().post("/", {"next": next_url})
        view = ResignFromRecruitment(request=request)
        # Act
        url = view.get_redirect_url()
        # Assert
        self.assertEqual(url, next_url)

    @patch("dashboard.views.messages")
    def test_post(self, mock_messages):
        # Arrange
        host = Organization.objects.create(domain="test.com", fullname="Test")
        person = Person.objects.create(
            personal="Test", family="User", email="test@user.com"
        )
        event = Event.objects.create(
            slug="test-event", host=host, start=date(2022, 2, 19), end=date(2022, 2, 20)
        )
        recruitment = InstructorRecruitment.objects.create(status="o", event=event)
        signup = InstructorRecruitmentSignup.objects.create(
            recruitment=recruitment, person=person
        )

        request = RequestFactory().post("/")
        request.user = person
        view = ResignFromRecruitment(kwargs={"signup_pk": signup.pk})

        # Act
        result = view.post(request)

        # Assert
        mock_messages.success.assert_called_once_with(
            request, f"Your teaching request was removed from recruitment {event}"
        )
        with self.assertRaises(InstructorRecruitmentSignup.DoesNotExist):
            signup.refresh_from_db()

        self.assertEqual(result.status_code, 302)
