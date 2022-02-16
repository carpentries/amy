from django.test import TestCase, override_settings
from django.test.client import RequestFactory

from communityroles.models import (
    CommunityRole,
    CommunityRoleConfig,
    CommunityRoleInactivation,
)
from dashboard.views import UpcomingTeachingOpportunitiesList
from workshops.models import Event, Organization, Person, Role, Task


class TestUpcomingTeachingOpportunityView(TestCase):
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
        request.user = person
        view = UpcomingTeachingOpportunitiesList(request=request)
        view.get_queryset()
        # Act & Assert
        with self.assertNumQueries(1):
            data = view.get_context_data(object_list=[])
        # Assert
        self.assertEqual(data["person"].num_taught, 1)
        self.assertEqual(data["person"].num_supporting, 2)
        self.assertEqual(data["person"].num_helper, 3)
