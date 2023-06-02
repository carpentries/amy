from datetime import datetime, timedelta

from trainings.filters import TraineeFilter
from trainings.models import Involvement
from trainings.views import all_trainees_queryset
from workshops.models import (
    Event,
    Person,
    TrainingProgress,
    TrainingRequest,
    TrainingRequirement,
)
from workshops.tests.base import TestBase


class TestTraineeFilter(TestBase):
    """
    A test should exist for each filter listed in test_fields().
    """

    def setUp(self) -> None:
        super().setUp()  # create some persons
        self._setUpEvents()  # create some events

        self.model = Person

        self.welcome = TrainingRequirement.objects.create(
            name="Welcome Session", url_required=False, event_required=False
        )
        self.event_required = TrainingRequirement.objects.create(
            name="Training", url_required=False, event_required=True
        )
        self.get_involved = TrainingRequirement.objects.create(
            name="Get Involved",
            url_required=False,
            event_required=False,
            involvement_required=True,
        )
        self.url_and_date_required, _ = Involvement.objects.get_or_create(
            name="GitHub Contribution",
            defaults={
                "display_name": "GitHub Contribution",
                "url_required": True,
                "date_required": True,
            },
        )
        self.notes_required, _ = Involvement.objects.get_or_create(
            name="Other without date",
            defaults={
                "display_name": "Other without date",
                "notes_required": True,
                "date_required": False,
            },
        )

        self.event = Event.objects.create(
            start=datetime.today() + timedelta(days=-31),
            end=datetime.today() + timedelta(days=-30),
            slug="training-event-ttt",
            host=self.org_alpha,
            url="http://example.org/training-event-ttt",
            country="US",
            venue="School",
            address="Overthere",
            latitude=1,
            longitude=2,
        )

        self.progress1 = TrainingProgress.objects.create(
            requirement=self.welcome,
            trainee=self.spiderman,
            state="p",
        )
        self.progress2 = TrainingProgress.objects.create(
            requirement=self.get_involved,
            involvement_type=self.url_and_date_required,
            trainee=self.ironman,
            state="n",
            date=datetime(2023, 5, 31),
            url="https://example.com",
        )
        self.progress3 = TrainingProgress.objects.create(
            requirement=self.welcome,
            trainee=self.hermione,
            state="p",
        )

        self.training_request = TrainingRequest.objects.create(
            person=self.spiderman,
            review_process="open",
            personal="Peter",
            family="Parker",
            email="peter@webslinger.net",
            state="a",
        )

        # get filterset
        self.filterset = TraineeFilter({})

        # run most tests only on actual trainees we've set up
        self.qs = all_trainees_queryset()

    def tearDown(self) -> None:
        # clean up progresses
        self.progress1.delete()
        self.progress2.delete()
        self.progress3.delete()
        self.training_request.delete()

        super().tearDown()

    def test_fields(self):
        # Arrange & Act stages happen in setUp()
        # Assert
        self.assertEqual(
            set(self.filterset.filters.keys()),
            {
                "search",
                "all_persons",
                "get_involved",
                "training_request",
                "is_instructor",
                "training",
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
        self.assertQuerysetEqual(result, [self.spiderman])

    def test_filter_search_email(self):
        # Arrange
        filter_name = "search"
        value = "peter@webslinger.net"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.spiderman])

    def test_filter_all_persons(self):
        # Arrange
        filter_name = "all_persons"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, Person.objects.all())

    def test_filter_get_involved(self):
        # Arrange
        filter_name = "get_involved"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.ironman])

    def test_filter_training_request_true(self):
        # Arrange
        filter_name = "training_request"
        value = True

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertIn(self.spiderman, result)
        self.assertNotIn(self.ironman, result)
        self.assertQuerysetEqual(result, [self.spiderman])

    def test_filter_training_request_false(self):
        # Arrange
        filter_name = "training_request"
        value = False

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertIn(self.ironman, result)
        self.assertIn(self.hermione, result)
        self.assertNotIn(self.spiderman, result)

    def test_filter_is_instructor(self):
        # Arrange
        filter_name = "is_instructor"
        value = "no"

        # Act
        result = self.filterset.filters[filter_name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.spiderman, self.ironman])

    def test_filter_training(self):
        # Arrange
        name = "training"
        value = self.event.pk

        # Act
        result = self.filterset.filters[name].filter(self.qs, value)

        # Assert
        self.assertQuerysetEqual(result, [self.spiderman])

    def test_filter_order_by(self):
        # Arrange
        filter_name = "order_by"
        fields = self.filterset.filters[filter_name].param_map
        results = {}
        # default ordering is ascending
        expected_results = {
            "last_login": [],
            "email": [self.ironman, self.spiderman],
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
            self.assertQuerysetEqual(results[field], expected_results[field])
