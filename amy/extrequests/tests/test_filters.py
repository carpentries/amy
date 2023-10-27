from datetime import datetime, timedelta

from dashboard.models import Continent
from extrequests.filters import TrainingRequestFilter, WorkshopRequestFilter
from workshops.models import (
    Curriculum,
    Event,
    Language,
    Membership,
    Role,
    Tag,
    Task,
    TrainingRequest,
    WorkshopRequest,
)
from workshops.tests.base import TestBase


class TestTrainingRequestFilter(TestBase):
    """
    A test should exist for each filter listed in test_fields().
    """

    def setUp(self) -> None:
        super().setUp()  # create some persons
        self._setUpTags()
        self._setUpRoles()

        self.model = TrainingRequest

        self.membership = Membership.objects.create(
            name="Alpha Organization",
            registration_code="valid123",
            agreement_start=datetime.today(),
            agreement_end=datetime.today() + timedelta(weeks=52),
        )
        self.ttt_event = Event.objects.create(
            slug="training-event-ttt",
            host=self.org_alpha,
        )
        self.ttt_event.tags.add(Tag.objects.get(name="TTT"))

        # add some training requests
        # spiderman: open application, accepted and fully matched
        self.request_spiderman = TrainingRequest.objects.create(
            person=self.spiderman,
            review_process="open",
            personal="Peter",
            family="Parker",
            email="peter@webslinger.net",
            state="a",
        )
        Task.objects.create(
            event=self.ttt_event,
            person=self.spiderman,
            role=Role.objects.get(name="learner"),
        )

        # ironman: preapproved application, pending, matched person
        self.request_ironman = TrainingRequest.objects.create(
            person=self.ironman,
            review_process="preapproved",
            member_code=self.membership.registration_code,
            personal="Tony",
            family="Stark",
            email="me@stark.com",
            affiliation="Stark Industries",
            location="New York City",
            state="p",
        )

        # blackwidow: invalid code, discarded, manually scored
        self.request_blackwidow = TrainingRequest.objects.create(
            review_process="preapproved",
            member_code="invalid",
            member_code_override=True,
            personal="Natasha",
            family="Romanova",
            email="natasha@romanova.com",
            state="d",
            score_manual=0,
        )

        # hermione: withdrawn
        self.request_hermione = TrainingRequest.objects.create(
            review_process="open",
            personal="Hermione",
            family="Granger",
            email="hermione@granger.co.uk",
            state="w",
        )

        # get filterset
        self.filterset = TrainingRequestFilter({})

        # get queryset
        self.qs = TrainingRequest.objects.all()

    def test_fields(self):
        # Arrange & Act stages happen in setUp()
        # Assert
        self.assertEqual(
            set(self.filterset.filters.keys()),
            {
                "search",
                "member_code",
                "state",
                "matched",
                "nonnull_manual_score",
                "invalid_member_code",
                "affiliation",
                "location",
                "order_by",
            },
        )

    def test_filter_search_name(self):
        # Arrange
        filter_name = "search"
        value = "Peter Parker"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_spiderman])

    def test_filter_search_email(self):
        # Arrange
        filter_name = "search"
        value = "peter@webslinger.net"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_spiderman])

    def test_filter_member_code(self):
        # Arrange
        filter_name = "member_code"
        value = "valid123"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_ironman])

    def test_filter_state__none(self):
        # Arrange
        filter_name = "state"
        value = None

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, self.qs, ordered=False)

    def test_filter_state__pending(self):
        # Arrange
        filter_name = "state"
        value = "p"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_ironman])

    def test_filter_state__accepted(self):
        # Arrange
        filter_name = "state"
        value = "a"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_spiderman])

    def test_filter_state__discarded(self):
        # Arrange
        filter_name = "state"
        value = "d"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_blackwidow])

    def test_filter_state__withdrawn(self):
        # Arrange
        filter_name = "state"
        value = "w"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_hermione])

    def test_filter_state__pending_or_accepted(self):
        # Arrange
        filter_name = "state"
        value = "pa"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(
            result, [self.request_spiderman, self.request_ironman], ordered=False
        )

    def test_filter_matched__unknown(self):
        # Arrange
        filter_name = "matched"
        value = None

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, self.qs, ordered=False)

    def test_filter_matched__unmatched(self):
        # Arrange
        filter_name = "matched"
        value = "u"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(
            result, [self.request_blackwidow, self.request_hermione], ordered=False
        )

    def test_filter_matched__matched_trainee_unmatched_training(self):
        # Arrange
        filter_name = "matched"
        value = "p"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_ironman])

    def test_filter_matched__matched_trainee_and_training(self):
        # Arrange
        filter_name = "matched"
        value = "t"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_spiderman])

    def test_filter_nonnull_manual_score(self):
        # Arrange
        filter_name = "nonnull_manual_score"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_blackwidow])

    def test_filter_invalid_member_code(self):
        # Arrange
        filter_name = "invalid_member_code"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_blackwidow])

    def test_filter_affiliation(self):
        # Arrange
        name = "affiliation"
        value = "stark"

        # Act
        result = self.filterset.filters[name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_ironman])

    def test_filter_location(self):
        # Arrange
        name = "location"
        value = "new york"

        # Act
        result = self.filterset.filters[name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request_ironman])

    def test_filter_order_by(self):
        # Arrange
        filter_name = "order_by"
        fields = self.filterset.filters[filter_name].param_map
        results = {}
        # manually set some scores to order by
        # blackwidow already has score_manual=0 from setUp()
        self.request_spiderman.score_manual = 3
        self.request_spiderman.save()
        self.request_ironman.score_manual = 2
        self.request_ironman.save()
        self.request_hermione.score_manual = 1
        self.request_hermione.save()

        # default ordering is ascending
        expected_results = {
            "created_at": [
                self.request_spiderman,
                self.request_ironman,
                self.request_blackwidow,
                self.request_hermione,
            ],
            "score_total": [
                self.request_blackwidow,
                self.request_hermione,
                self.request_ironman,
                self.request_spiderman,
            ],
        }

        # Act
        for field in fields.keys():
            results[field] = self.filterset.filters[filter_name].filter(
                self.qs, [field]
            )

        # Assert
        # we don't have any unexpected fields
        self.assertEqual(fields.keys(), expected_results.keys())
        # each field was filtered correctly
        for field in fields.keys():
            self.assertQuerysetEqual(
                results[field], expected_results[field], ordered=True
            )


class TestWorkshopRequestFilter(TestBase):
    """
    A test should exist for each filter listed in test_fields().
    """

    def setUp(self) -> None:
        super().setUp()  # create some persons
        self._setUpTags()
        self._setUpRoles()

        self.model = WorkshopRequest

        self.membership = Membership.objects.create(
            name="Alpha Organization",
            registration_code="valid123",
            agreement_start=datetime.today(),
            agreement_end=datetime.today() + timedelta(weeks=52),
        )

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

        # add some workshop requests
        self.request1 = WorkshopRequest.objects.create(**kwargs)
        kwargs["institution_other_name"] = ""
        kwargs["institution"] = self.org_alpha
        kwargs["assigned_to"] = self.spiderman
        kwargs["country"] = "US"
        kwargs["state"] = "d"
        self.request2 = WorkshopRequest.objects.create(**kwargs)
        self.request2.requested_workshop_types.set(
            Curriculum.objects.filter(slug="dc-ecology-r")
        )
        kwargs["member_code"] = "valid123"
        kwargs.pop("assigned_to")
        kwargs["state"] = "a"
        self.request3 = WorkshopRequest.objects.create(**kwargs)

        # get filterset
        self.filterset = WorkshopRequestFilter({})

        # get queryset
        self.qs = WorkshopRequest.objects.all()

    def test_fields(self):
        # Arrange & Act stages happen in setUp()
        # Assert
        self.assertEqual(
            set(self.filterset.filters.keys()),
            {
                "state",
                "assigned_to",
                "country",
                "continent",
                "requested_workshop_types",
                "unused_member_code",
                "order_by",
            },
        )

    def test_filter_state__any(self):
        # Arrange
        filter_name = "state"
        value = ""

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, self.qs, ordered=False)

    def test_filter_state__pending(self):
        # Arrange
        filter_name = "state"
        value = "p"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request1])

    def test_filter_state__accepted(self):
        # Arrange
        filter_name = "state"
        value = "a"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request3])

    def test_filter_state_discarded(self):
        # Arrange
        filter_name = "state"
        value = "d"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request2])

    def test_filter_assigned_to(self):
        # Arrange
        filter_name = "assigned_to"
        value = self.spiderman

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request2])

    def test_filter_country(self):
        # Arrange
        filter_name = "country"
        value = "GB"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request1])

    def test_filter_continent(self):
        # Arrange
        filter_name = "continent"
        value = Continent.objects.get(name="Europe").pk

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request1])

    def test_filter_requested_workshop_types(self):
        # Arrange
        filter_name = "requested_workshop_types"
        value = Curriculum.objects.filter(slug="dc-ecology-r")

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request2])

    def test_filter_unused_member_code(self):
        # Arrange
        filter_name = "unused_member_code"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.request2])

    def test_filter_order_by(self):
        # Arrange
        filter_name = "order_by"
        fields = self.filterset.filters[filter_name].param_map
        results = {}

        # default ordering is ascending
        expected_results = {
            "created_at": [self.request1, self.request2, self.request3],
        }

        # Act
        for field in fields.keys():
            results[field] = self.filterset.filters[filter_name].filter(
                self.qs, [field]
            )

        # Assert
        # we don't have any unexpected fields
        self.assertEqual(fields.keys(), expected_results.keys())
        # each field was filtered correctly
        for field in fields.keys():
            self.assertQuerysetEqual(
                results[field], expected_results[field], ordered=True
            )
