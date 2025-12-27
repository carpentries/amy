import csv
import io

from django.urls import reverse

from src.workshops.models import Badge, Event, Organization, Role, Tag, Task
from src.workshops.tests.base import TestBase
from src.workshops.views import _workshop_staff_query


class TestLocateWorkshopStaff(TestBase):
    """Test cases for locating workshop staff."""

    def setUp(self) -> None:
        super().setUp()
        self._setUpTags()
        self._setUpRoles()
        self._setUpUsersAndLogin()
        self._setUpSingleInstructorBadges()
        self._setUpCommunityRoles()
        self.url = reverse("workshop_staff")

    def test_non_instructors_and_instructors_returned_by_search(self) -> None:
        """Ensure search returns everyone with defined airport."""
        response = self.client.get(
            self.url,
            {
                "airport_iata": "CDG",
            },
        )
        self.assertEqual(response.status_code, 200)

        # instructors
        self.assertIn(self.hermione, response.context["persons"])
        self.assertIn(self.harry, response.context["persons"])
        self.assertIn(self.ron, response.context["persons"])
        # non-instructors
        self.assertIn(self.spiderman, response.context["persons"])
        self.assertIn(self.ironman, response.context["persons"])
        self.assertIn(self.blackwidow, response.context["persons"])

    def test_match_on_one_skill(self) -> None:
        """Ensure people with correct skill are returned."""
        response = self.client.get(
            self.url,
            query_params={
                "airport_iata": "LAX",
                "lessons": [self.git.pk],
            },
        )
        self.assertEqual(response.status_code, 200)
        # lessons
        self.assertIn(self.git, response.context["lessons"])

        # instructors
        self.assertIn(self.hermione, response.context["persons"])
        self.assertNotIn(self.harry, response.context["persons"])
        self.assertIn(self.ron, response.context["persons"])
        # non-instructors
        self.assertNotIn(self.spiderman, response.context["persons"])
        self.assertNotIn(self.ironman, response.context["persons"])
        self.assertNotIn(self.blackwidow, response.context["persons"])

    def test_match_instructors_on_two_skills(self) -> None:
        """Ensure people with correct skills are returned."""
        response = self.client.get(
            self.url,
            query_params={
                "airport_iata": "LAX",
                "lessons": [self.git.pk, self.sql.pk],
            },
        )
        self.assertEqual(response.status_code, 200)
        # lessons
        self.assertIn(self.git, response.context["lessons"])
        self.assertIn(self.sql, response.context["lessons"])

        # instructors
        self.assertIn(self.hermione, response.context["persons"])
        self.assertNotIn(self.harry, response.context["persons"])
        self.assertNotIn(self.ron, response.context["persons"])
        # non-instructors
        self.assertNotIn(self.spiderman, response.context["persons"])
        self.assertNotIn(self.ironman, response.context["persons"])
        self.assertNotIn(self.blackwidow, response.context["persons"])

    def test_match_by_country(self) -> None:
        """Ensure people from France are returned."""
        response = self.client.get(
            self.url,
            {
                "country": ["FR"],
            },
        )
        self.assertEqual(response.status_code, 200)

        # instructors
        self.assertIn(self.hermione, response.context["persons"])
        self.assertNotIn(self.harry, response.context["persons"])
        self.assertNotIn(self.ron, response.context["persons"])
        # non-instructors
        self.assertNotIn(self.spiderman, response.context["persons"])
        self.assertNotIn(self.ironman, response.context["persons"])
        self.assertIn(self.blackwidow, response.context["persons"])  # through airport

    def test_match_by_multiple_countries(self) -> None:
        """Ensure people from France and Poland are returned."""
        response = self.client.get(
            self.url,
            {
                "country": ["FR", "PL"],
            },
        )
        self.assertEqual(response.status_code, 200)

        # instructors
        self.assertIn(self.hermione, response.context["persons"])
        self.assertIn(self.harry, response.context["persons"])
        self.assertNotIn(self.ron, response.context["persons"])
        # non-instructors
        self.assertNotIn(self.spiderman, response.context["persons"])
        self.assertNotIn(self.ironman, response.context["persons"])
        self.assertIn(self.blackwidow, response.context["persons"])  # through airport

    def test_match_gender(self) -> None:
        """Ensure only people with specific gender are returned."""
        response = self.client.get(
            self.url,
            {
                "airport_iata": "CDG",
                "gender": "F",
            },
        )
        self.assertEqual(response.status_code, 200)

        # instructors
        self.assertIn(self.hermione, response.context["persons"])
        self.assertNotIn(self.harry, response.context["persons"])
        self.assertNotIn(self.ron, response.context["persons"])
        # non-instructors
        self.assertNotIn(self.spiderman, response.context["persons"])
        self.assertNotIn(self.ironman, response.context["persons"])
        self.assertIn(self.blackwidow, response.context["persons"])

    def test_is_instructor(self) -> None:
        """Ensure people with instructor badges are returned by search. The
        search is OR'ed, so should return people with any of the selected
        badges."""
        response = self.client.get(
            self.url,
            {"airport_iata": "CDG", "is_instructor": True},  # type: ignore
        )
        self.assertEqual(response.status_code, 200)

        # instructors
        self.assertIn(self.hermione, response.context["persons"])  # SWC, DC,LC
        self.assertIn(self.harry, response.context["persons"])  # SWC, DC
        self.assertIn(self.ron, response.context["persons"])  # SWC only
        # non-instructors
        self.assertNotIn(self.spiderman, response.context["persons"])
        self.assertNotIn(self.ironman, response.context["persons"])
        self.assertNotIn(self.blackwidow, response.context["persons"])

        response = self.client.get(self.url, {"airport_iata": "CDG"})
        self.assertEqual(response.status_code, 200)

        # instructors
        self.assertIn(self.hermione, response.context["persons"])  # SWC, DC,LC
        self.assertIn(self.harry, response.context["persons"])  # SWC, DC
        self.assertIn(self.ron, response.context["persons"])  # SWC only
        # non-instructors
        self.assertIn(self.spiderman, response.context["persons"])
        self.assertIn(self.ironman, response.context["persons"])
        self.assertIn(self.blackwidow, response.context["persons"])

    def test_match_on_one_language(self) -> None:
        """Ensure people with one particular language preference
        are returned by search."""
        # prepare langauges
        self._setUpLanguages()
        # Ron can communicate in English
        self.ron.languages.add(self.english)
        self.ron.save()
        # Harry can communicate in French
        self.harry.languages.add(self.french)
        self.harry.save()

        response = self.client.get(
            self.url,
            {
                "languages": [self.french.pk],
            },
        )
        self.assertEqual(response.status_code, 200)

        self.assertIn(self.harry, response.context["persons"])
        self.assertNotIn(self.ron, response.context["persons"])

    def test_match_on_many_language(self) -> None:
        """Ensure people with a set of language preferences
        are returned by search."""
        # prepare langauges
        self._setUpLanguages()
        # Ron can communicate in many languages
        self.ron.languages.add(self.english, self.french)
        self.ron.save()
        # Harry is mono-lingual
        self.harry.languages.add(self.french)
        self.harry.save()

        response = self.client.get(
            self.url,
            {
                "languages": [self.english.pk, self.french.pk],
            },
        )
        self.assertEqual(response.status_code, 200)

        self.assertIn(self.ron, response.context["persons"])
        self.assertNotIn(self.harry, response.context["persons"])
        self.assertIn(self.ron, response.context["persons"])
        self.assertNotIn(self.harry, response.context["persons"])

    def test_match_on_one_domain(self) -> None:
        """Ensure people with one particular knowledge domain preference
        are returned by search."""
        # prepare knowledge domains
        self._setUpDomains()
        # Ron has a humanities knowledge domain
        self.ron.domains.add(self.humanities)
        # Harry has a chemistry knowledge domain
        self.harry.domains.add(self.chemistry)

        response = self.client.get(
            self.url,
            {
                "domains": [self.chemistry.pk],
            },
        )
        self.assertEqual(response.status_code, 200)

        self.assertIn(self.harry, response.context["persons"])
        self.assertNotIn(self.ron, response.context["persons"])

    def test_match_on_many_domains(self) -> None:
        """Ensure people with a set of knowledge domain preferences
        are returned by search."""
        # prepare knowledge domains
        self._setUpDomains()
        # Ron has a humanities and chemistry knowledge domain
        self.ron.domains.add(self.humanities, self.chemistry)
        # Harry has a chemistry knowledge domain
        self.harry.domains.add(self.chemistry)

        response = self.client.get(
            self.url,
            {
                "domains": [self.chemistry.pk, self.humanities.pk],
            },
        )
        self.assertEqual(response.status_code, 200)

        self.assertIn(self.ron, response.context["persons"])
        self.assertNotIn(self.harry, response.context["persons"])

    def test_roles(self) -> None:
        """Ensure people with at least one helper/organizer roles are returned
        by search."""
        # prepare events and tasks
        self._setUpEvents()
        helper_role = Role.objects.get(name="helper")
        organizer_role = Role.objects.get(name="organizer")

        Task.objects.create(role=helper_role, person=self.spiderman, event=Event.objects.all()[0])
        Task.objects.create(role=organizer_role, person=self.blackwidow, event=Event.objects.all()[0])

        response = self.client.get(
            self.url,
            {
                "airport_iata": "CDG",
                "was_helper": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["persons"]), [self.spiderman])

        response = self.client.get(
            self.url,
            {
                "airport_iata": "CDG",
                "was_organizer": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["persons"]), [self.blackwidow])

    def test_form_logic(self) -> None:
        """Check if logic preventing searching from multiple fields,
        except lat+lng pair, and allowing searching from no location field,
        works."""
        test_vectors = [
            (True, {"latitude": 1, "longitude": 2}),
            (True, dict()),
            (False, {"latitude": 1}),
            (False, {"longitude": 1, "country": ["BG"]}),
            (False, {"latitude": 1, "longitude": 2, "country": ["BG"]}),
            (
                False,
                {
                    "latitude": 1,
                    "longitude": 2,
                    "country": ["BG"],
                    "airport_iata": "CDG",
                },
            ),
        ]

        for form_pass, data in test_vectors:
            params = dict(submit="Submit")
            params.update(data)  # type: ignore
            rv = self.client.get(self.url, params)
            form = rv.context["form"]
            self.assertEqual(form.is_valid(), form_pass, form.errors)

    def test_searching_trainees(self) -> None:
        """Make sure finding trainees works. This test additionally checks for
        a more complex cases:
        * a trainee who participated in only a stalled TTT workshop
        * a trainee who participated in only a non-stalled TTT workshop
        * a trainee who participated in both.
        """
        response = self.client.get(
            self.url,
            {
                "airport_iata": "CDG",
                "is_in_progress_trainee": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["persons"]), [])

        TTT = Tag.objects.get(name="TTT")
        stalled = Tag.objects.get(name="stalled")
        e1 = Event.objects.create(slug="TTT-event", host=Organization.objects.all()[0])
        e1.tags.set([TTT])
        e2 = Event.objects.create(slug="stalled-TTT-event", host=Organization.objects.all()[0])
        e2.tags.set([TTT, stalled])

        learner = Role.objects.get(name="learner")
        # Ron is an instructor, so he should not be available as a trainee
        Task.objects.create(person=self.ron, event=e1, role=learner)
        Task.objects.create(person=self.ron, event=e2, role=learner)
        # Black Widow, on the other hand, is now practising to become certified
        # SWC instructor!
        Task.objects.create(person=self.blackwidow, event=e1, role=learner)
        # Spiderman tried to became an instructor once, is enrolled in
        # non-stalled TTT event
        Task.objects.create(person=self.spiderman, event=e1, role=learner)
        Task.objects.create(person=self.spiderman, event=e2, role=learner)
        # Ironman on the other hand didn't succeed in getting an instructor
        # badge (he's enrolled in TTT-stalled event)
        Task.objects.create(person=self.ironman, event=e2, role=learner)

        # repeat the query
        response = self.client.get(
            self.url,
            {
                "airport_iata": "CDG",
                "is_in_progress_trainee": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.context["persons"]),
            set(
                [
                    self.blackwidow,
                    self.spiderman,
                ]
            ),
        )

    def test_searching_trainers(self) -> None:
        """Make sure people with Trainer badge are shown correctly."""
        response = self.client.get(self.url, dict(is_trainer="on"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["persons"]), [])
        trainer = Badge.objects.get(name="trainer")
        self.harry.award_set.create(badge=trainer)
        response = self.client.get(self.url, dict(is_trainer="on"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["persons"]), [self.harry])


class TestWorkshopStaffCSV(TestBase):
    """Test cases for downloading workshop staff search results as CSV."""

    def setUp(self) -> None:
        super().setUp()
        self._setUpTags()
        self._setUpRoles()
        self._setUpUsersAndLogin()

        self.url = reverse("workshop_staff_csv")

    def test_header_row(self) -> None:
        """Ensure header contains the data we want."""
        rv = self.client.get(self.url)
        first_row = rv.content.decode("utf-8").splitlines()[0]
        first_row_expected = (
            "Name,Email,Is instructor,Is trainer,Taught times,Is trainee,Airport,Country,Lessons,Affiliation"
        )

        self.assertEqual(first_row, first_row_expected)

    def test_results(self) -> None:
        """Test for the workshop staff CSV output."""
        rv = self.client.get(self.url)
        reader = csv.DictReader(io.StringIO(rv.content.decode("utf-8")))
        results = _workshop_staff_query()
        for row, expected in zip(reader, results, strict=False):
            self.assertEqual(row["Name"], expected.full_name)
            self.assertEqual(row["Email"] or None, expected.email)
            self.assertEqual(
                row["Is instructor"],
                "yes" if expected.is_instructor else "no",
            )
            self.assertEqual(row["Is trainer"], "yes" if expected.is_trainer else "no")
            self.assertEqual(row["Taught times"], str(expected.num_instructor))
            self.assertEqual(row["Is trainee"], "yes" if expected.is_trainee else "no")
            self.assertEqual(row["Airport"], str(expected.airport_iata))
            self.assertEqual(row["Country"], expected.country.name)
            self.assertEqual(row["Affiliation"], expected.affiliation)
