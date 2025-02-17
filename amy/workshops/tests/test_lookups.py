from datetime import date
from typing import Optional

from django.contrib.contenttypes.models import ContentType
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q
from django.http.response import Http404
from django.test import RequestFactory
from django.urls import reverse

from workshops.lookups import (
    AwardLookupView,
    EventLookupForAwardsView,
    EventLookupView,
    GenericObjectLookupView,
    KnowledgeDomainLookupView,
    MembershipLookupForTasksView,
    MembershipLookupView,
    TTTEventLookupView,
    urlpatterns,
)
from workshops.models import (
    Award,
    Badge,
    Event,
    KnowledgeDomain,
    Lesson,
    Membership,
    Person,
    Role,
    Tag,
    TrainingProgress,
    TrainingRequest,
    TrainingRequirement,
)
from workshops.tests.base import (
    TestBase,
    TestViewPermissionsMixin,
    consent_to_all_required_consents,
)


class TestLookups(TestBase):
    """Test suite for Django-Autocomplete-Light lookups."""

    def setUp(self):
        # prepare urlpatterns; only include lookup views that are restricted
        # to logged-in users and/or admins
        self.patterns_nonrestricted = ("language-lookup",)
        self.urlpatterns = filter(lambda pattern: pattern.name not in self.patterns_nonrestricted, urlpatterns)

    def test_login_regression(self):
        """Make sure lookups are login-protected"""
        for pattern in self.urlpatterns:
            rv = self.client.get(reverse(pattern.name))
            self.assertEqual(rv.status_code, 403, pattern.name)  # forbidden

        self._setUpUsersAndLogin()
        for pattern in self.urlpatterns:
            rv = self.client.get(reverse(pattern.name))
            self.assertEqual(rv.status_code, 200, pattern.name)  # OK


class TestKnowledgeDomainLookupView(TestBase):
    def setUpView(self, term: str = "") -> KnowledgeDomainLookupView:
        # path doesn't matter
        request = RequestFactory().get("/")
        view = KnowledgeDomainLookupView(request=request, term=term)
        return view

    def test_get_queryset_no_term(self):
        # Arrange
        view = self.setUpView()
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, KnowledgeDomain.objects.all(), ordered=False)

    def test_get_queryset_simple_term(self):
        # Arrange
        term = "ed"
        view = self.setUpView(term=term)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(
            queryset,
            KnowledgeDomain.objects.filter(name__icontains=term),
            ordered=False,
        )


class TestAwardLookupView(TestBase):
    def setUpView(self, term: str = "", badge: Optional[int] = None) -> AwardLookupView:
        # path doesn't matter
        request = RequestFactory().get("/" if badge is None else f"/?badge={badge}")
        view = AwardLookupView(request=request, term=term)
        return view

    def test_get_queryset_no_term(self):
        # Arrange
        view = self.setUpView()
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertEqual(set(queryset), set(Award.objects.all()))

    def test_get_queryset_simple_term(self):
        # Arrange
        term = "term"
        view = self.setUpView(term=term)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertEqual(
            set(queryset),
            set(
                Award.objects.filter(
                    Q(person__personal__icontains=term)
                    | Q(person__middle__icontains=term)
                    | Q(person__family__icontains=term)
                    | Q(person__email__icontains=term)
                    | Q(badge__name__icontains=term)
                )
            ),
        )

    def test_get_queryset_badge(self):
        # Arrange
        badge = self.swc_instructor.pk
        view = self.setUpView(badge=badge)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertEqual(set(queryset), set(Award.objects.filter(badge__pk=badge)))

    def test_get_queryset_badge_and_term(self):
        # Arrange
        badge = self.swc_instructor.pk
        term = "term"
        view = self.setUpView(term=term, badge=badge)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertEqual(
            set(queryset),
            set(
                Award.objects.filter(badge__pk=badge).filter(
                    Q(person__personal__icontains=term)
                    | Q(person__middle__icontains=term)
                    | Q(person__family__icontains=term)
                    | Q(person__email__icontains=term)
                    | Q(badge__name__icontains=term)
                )
            ),
        )


class TestEventLookupView(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpTags()

        self.event = Event.objects.create(slug="queryset-test", host=self.org_alpha)
        self.event_2 = Event.objects.create(slug="different-slug-test", host=self.org_alpha)
        self.ttt_event = Event.objects.create(slug="queryset-test-ttt", host=self.org_alpha)
        self.ttt_event.tags.add(Tag.objects.get(name="TTT"))

    def setUpView(self, term: str = "", person: Optional[int] = None) -> EventLookupView:
        # path doesn't matter
        request = RequestFactory().get("/" if person is None else f"/?person={person}")
        view = EventLookupView(request=request, term=term)
        return view

    def test_get_queryset_no_term(self):
        # Arrange
        view = self.setUpView()
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, Event.objects.all())

    def test_get_queryset_term(self):
        # Arrange
        term = "query"
        view = self.setUpView(term=term)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.event, self.ttt_event], ordered=False)


class TestEventLookupForAwardsView(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpTags()

        self.event = Event.objects.create(slug="queryset-test", host=self.org_alpha)
        self.ttt_event = Event.objects.create(slug="queryset-test-ttt", host=self.org_alpha)
        self.ttt_event.tags.add(Tag.objects.get(name="TTT"))
        self.ttt_event.task_set.create(person=self.blackwidow, role=Role.objects.get(name="learner"))
        TrainingProgress.objects.create(
            trainee=self.blackwidow,
            requirement=TrainingRequirement.objects.get(name="Training"),
            state="p",
            event=self.ttt_event,
        )
        self.ttt_event_2 = Event.objects.create(slug="different-slug-ttt", host=self.org_alpha)
        self.ttt_event_2.tags.add(Tag.objects.get(name="TTT"))
        self.ttt_event_2.task_set.create(person=self.blackwidow, role=Role.objects.get(name="learner"))
        TrainingProgress.objects.create(
            trainee=self.blackwidow,
            requirement=TrainingRequirement.objects.get(name="Training"),
            state="p",
            event=self.ttt_event_2,
        )

    def setUpView(
        self, term: str = "", person: Optional[int] = None, badge: Optional[int] = None
    ) -> EventLookupForAwardsView:
        # path doesn't matter
        request = RequestFactory().get(f"/?person={person if person else ''}&badge={badge if badge else ''}")
        view = EventLookupForAwardsView(request=request, term=term)
        return view

    def test_get_queryset_no_args(self):
        # Arrange
        view = self.setUpView()
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, Event.objects.all())

    def test_get_queryset_term(self):
        # Arrange
        term = "query"
        view = self.setUpView(term=term)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.event, self.ttt_event], ordered=False)

    def test_get_queryset_person(self):
        """Person alone should not change results."""
        # Arrange
        view = self.setUpView(person=self.blackwidow.pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(
            queryset,
            Event.objects.all(),
        )

    def test_get_queryset_badge(self):
        """Badge alone should not change results."""
        # Arrange
        view = self.setUpView(badge=self.instructor_badge.pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(
            queryset,
            Event.objects.all(),
        )

    def test_get_queryset_person_and_instructor_badge(self):
        """Person and instructor badge combined should change results."""
        # Arrange
        view = self.setUpView(person=self.blackwidow.pk, badge=self.instructor_badge.pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.ttt_event, self.ttt_event_2], ordered=False)

    def test_get_queryset_person_and_non_instructor_badge(self):
        """Person and maintainer badge combined should not change results."""
        # Arrange
        view = self.setUpView(person=self.blackwidow.pk, badge=Badge.objects.get(name="maintainer").pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(
            queryset,
            Event.objects.all(),
        )

    def test_get_queryset_person_and_badge_and_term(self):
        # Arrange
        term = "query"
        view = self.setUpView(term=term, person=self.blackwidow.pk, badge=self.instructor_badge.pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(
            queryset,
            [self.ttt_event],
        )


class TestTTTEventLookupView(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpTags()

        self.event = Event.objects.create(slug="queryset-test", host=self.org_alpha)
        self.event.tags.add(Tag.objects.get(name="TTT"))
        self.event.task_set.create(person=self.blackwidow, role=Role.objects.get(name="learner"))
        self.event2 = Event.objects.create(slug="different-slug", host=self.org_alpha)
        self.event2.tags.add(Tag.objects.get(name="TTT"))
        self.event2.task_set.create(person=self.blackwidow, role=Role.objects.get(name="learner"))

    def setUpView(self, term: str = "", trainee: Optional[int] = None) -> TTTEventLookupView:
        # path doesn't matter
        request = RequestFactory().get("/" if trainee is None else f"/?trainee={trainee}")
        view = TTTEventLookupView(request=request, term=term)
        return view

    def test_get_queryset_no_term_no_trainee(self):
        # Arrange
        view = self.setUpView()
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, Event.objects.ttt())

    def test_get_queryset_term(self):
        # Arrange
        term = "query"
        view = self.setUpView(term=term)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.event])

    def test_get_queryset_trainee(self):
        # Arrange
        view = self.setUpView(trainee=self.blackwidow.pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.event, self.event2], ordered=False)

    def test_get_queryset_trainee_and_term(self):
        # Arrange
        term = "query"
        view = self.setUpView(term=term, trainee=self.blackwidow.pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(
            queryset,
            [self.event],
        )


class TestMembershipLookupView(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpTags()

        self.membership_alpha = Membership.objects.create(
            name="Alpha Organization",
            variant="bronze",
            agreement_start=date(2023, 8, 15),
            agreement_end=date(2024, 8, 14),
            contribution_type="financial",
            registration_code="alpha44",
        )
        self.membership_beta = Membership.objects.create(
            name="Beta Organization Unique",
            variant="bronze",
            agreement_start=date(2023, 9, 15),
            agreement_end=date(2024, 9, 14),
            contribution_type="financial",
            registration_code="beta55",
        )
        self.membership_gamma = Membership.objects.create(
            name="Gamma Organization",
            variant="silver",
            agreement_start=date(2023, 10, 15),
            agreement_end=date(2023, 11, 14),
            contribution_type="financial",
            registration_code="gamma66",
        )

    def setUpView(self, term: str = "") -> MembershipLookupView:
        # path doesn't matter
        request = RequestFactory().get("/")
        view = MembershipLookupView(request=request, term=term)
        return view

    def test_get_queryset_no_term(self):
        # Arrange
        view = self.setUpView()
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, Membership.objects.all(), ordered=False)

    def test_get_queryset_term__date(self):
        # Arrange
        term = "2023-08-30"
        view = self.setUpView(term=term)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.membership_alpha], ordered=False)

    def test_get_queryset_term__organization_name(self):
        # Arrange
        term = "alpha"
        view = self.setUpView(term=term)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.membership_alpha], ordered=False)

    def test_get_queryset_term__membership_name(self):
        # Arrange
        term = "unique"
        view = self.setUpView(term=term)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.membership_beta], ordered=False)

    def test_get_queryset_term__variant(self):
        # Arrange
        term = "bronze"
        view = self.setUpView(term=term)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.membership_alpha, self.membership_beta], ordered=False)


class TestMembershipLookupForTasksView(TestMembershipLookupView):
    def setUp(self):
        super().setUp()

        self.role = Role.objects.get(name="learner")

        self.event = Event.objects.create(slug="test-event", host=self.org_alpha)
        self.ttt_event = Event.objects.create(slug="test-ttt", host=self.org_alpha)
        self.ttt_event.tags.add(Tag.objects.get(name="TTT"))

        # create some training requests
        TrainingRequest.objects.create(person=self.blackwidow, member_code=self.membership_alpha.registration_code)
        TrainingRequest.objects.create(person=self.blackwidow, member_code=self.membership_beta.registration_code)

    def setUpView(
        self,
        term: str = "",
        person: Optional[int] = None,
        role: Optional[int] = None,
        event: Optional[int] = None,
    ) -> MembershipLookupForTasksView:
        # path doesn't matter
        request = RequestFactory().get(
            f"/?person={person if person else ''}" f"&role={role if role else ''}" f"&event={event if event else ''}"
        )
        view = MembershipLookupForTasksView(request=request, term=term)
        return view

    def test_get_queryset_no_args(self):
        # Arrange
        view = self.setUpView()
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, Membership.objects.all(), ordered=False)

    def test_get_queryset_person(self):
        """Person alone should not change results."""
        # Arrange
        view = self.setUpView(person=self.blackwidow.pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, Membership.objects.all(), ordered=False)

    def test_get_queryset_role(self):
        """Role alone should not change results."""
        # Arrange
        view = self.setUpView(role=self.role.pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, Membership.objects.all(), ordered=False)

    def test_get_queryset_event(self):
        """Event alone should not change results."""
        # Arrange
        view = self.setUpView(event=self.ttt_event.pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, Membership.objects.all(), ordered=False)

    def test_get_queryset_person_and_non_learner_role_and_ttt_event(self):
        """Any query with a non-learner role should not change results."""
        # Arrange
        view = self.setUpView(
            person=self.blackwidow.pk,
            role=Role.objects.get(name="instructor").pk,
            event=self.ttt_event.pk,
        )
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, Membership.objects.all(), ordered=False)

    def test_get_queryset_person_and_learner_role_and_non_ttt_event(self):
        """Any query with a non-TTT event should not change results."""
        # Arrange
        view = self.setUpView(
            person=self.blackwidow.pk,
            role=self.role.pk,
            event=self.event.pk,
        )
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, Membership.objects.all(), ordered=False)

    def test_get_queryset_person_and_learner_role_and_ttt_event(self):
        """Person, role, and event combined should change results."""
        # Arrange
        view = self.setUpView(person=self.blackwidow.pk, role=self.role.pk, event=self.ttt_event.pk)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.membership_alpha, self.membership_beta], ordered=False)

    def test_get_queryset_person_and_learner_role_and_ttt_event_and_term(self):
        """Person, role, event, and term combined should change results."""
        # Arrange
        term = "alpha"
        view = self.setUpView(
            term=term,
            person=self.blackwidow.pk,
            role=self.role.pk,
            event=self.ttt_event.pk,
        )
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertQuerySetEqual(queryset, [self.membership_alpha], ordered=False)


class TestGenericObjectLookupView(TestBase):
    def setUpRequest(self, path: str) -> WSGIRequest:
        return RequestFactory().get(path)

    def setUpView(self, content_type: Optional[ContentType] = None) -> GenericObjectLookupView:
        # path doesn't matter
        path = "/"
        if content_type:
            path = f"/?content_type={content_type.pk}"
        request = self.setUpRequest(path)
        view = GenericObjectLookupView(request=request, content_type=content_type)
        return view

    def test_get_queryset_no_content_type_returns_empty_results(self):
        # Arrange
        view = self.setUpView()
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertTrue(queryset.model is None)
        # QuerySets created without model param don't support comparisons to
        # EmptyQuerySet or checking if underlying `query` is empty. So the easiest way
        # I figured was to check if `.model` is None.

    def test_get_queryset_invalid_content_type_raises_404(self):
        # Arrange
        view = self.setUpView(content_type=ContentType(pk=1000000, app_label="Test", model="Test"))
        # Act & Assert
        with self.assertRaises(Http404):
            view.get_queryset()

    def test_get_queryset_concrete_content_type_returns_queryset_for_that_model(self):
        # Arrange
        content_type = ContentType.objects.get_for_model(Lesson)
        view = self.setUpView(content_type=content_type)
        # Act
        queryset = view.get_queryset()
        # Assert
        self.assertEqual(queryset.model, Lesson)
        self.assertEqual(set(queryset), set(Lesson.objects.all()))

    def test_get_response(self):
        # Arrange
        content_type = ContentType.objects.get_for_model(Badge)
        view = self.setUpView(content_type=content_type)
        request = self.setUpRequest("/")

        # Act
        result = view.get(request)
        # Assert
        self.assertEqual(
            result.content.decode("utf-8"),
            '{"results": ['
            '{"text": "Software Carpentry Instructor", "id": 1}, '
            '{"text": "Data Carpentry Instructor", "id": 2}, '
            '{"text": "Maintainer", "id": 3}, '
            '{"text": "Trainer", "id": 4}, '
            '{"text": "Mentor", "id": 5}, '
            '{"text": "Mentee", "id": 6}, '
            '{"text": "Library Carpentry Instructor", "id": 7}, '
            '{"text": "Instructor", "id": '
            f"{self.instructor_badge.pk}"
            "}]}",
        )

    def test_permissions_no_content_type(self):
        # Arrange
        content_type = ""
        view = self.setUpView()
        # Act
        result = view.test_func(content_type)
        # Assert
        self.assertFalse(result)

    def test_permissions_content_type_doesnt_exist(self):
        # Arrange
        content_type = "-1"
        view = self.setUpView()
        # Act
        result = view.test_func(content_type)
        # Assert
        self.assertFalse(result)


class TestGenericObjectLookupViewUserPermissions(TestViewPermissionsMixin, TestBase):
    """Integration tests for user passing test on specific Model instances.

    If user has "view_model" permissions, they should be let in."""

    def setUp(self):
        super().setUp()
        self.user = Person.objects.create_user(
            "testuser",
            "Personal",
            "Family",
            "personal.family@example.org",
            "secretpassword",
        )
        self.model = Badge
        self.permissions = ["view_badge"]
        self.methods = ["GET"]
        self.content_type = ContentType.objects.get_for_model(self.model)
        self.view_url = reverse("generic-object-lookup") + f"?content_type={self.content_type.pk}"
        # prevent redirect to accept terms from middleware
        consent_to_all_required_consents(self.user)
