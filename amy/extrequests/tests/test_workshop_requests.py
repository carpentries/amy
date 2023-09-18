from datetime import date, timedelta

from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from autoemails.models import EmailTemplate, RQJob, Trigger
from autoemails.tests.base import FakeRedisTestCaseMixin
from extrequests.forms import WorkshopRequestBaseForm
import extrequests.views
from workshops.forms import EventCreateForm
from workshops.models import (
    Curriculum,
    Event,
    InfoSource,
    Language,
    Membership,
    Organization,
    Role,
    Tag,
    Task,
    WorkshopRequest,
)
from workshops.tests.base import FormTestHelper, TestBase


class TestWorkshopRequestBaseForm(FormTestHelper, TestBase):
    """Test base form validation."""

    def setUpMembership(self):
        Membership.objects.create(
            name="Alpha Organization",
            variant="bronze",
            agreement_start=date(2023, 8, 15),
            agreement_end=date(2024, 8, 14),
            contribution_type="financial",
            registration_code="valid123",
        )

    def test_minimal_form(self):
        """Test if minimal form works."""
        data = {
            "personal": "Harry",
            "family": "Potter",
            "email": "hpotter@magic.gov",
            "institution_other_name": "Ministry of Magic",
            "institution_other_URL": "magic.gov.uk",
            "membership_affiliation": "no",
            "membership_code": "",
            "location": "London",
            "country": "GB",
            "requested_workshop_types": [
                Curriculum.objects.default_order(allow_unknown=False, allow_other=False)
                .filter(active=True)
                .first()
                .pk,
            ],
            "preferred_dates": "{:%Y-%m-%d}".format(date.today()),
            "other_preferred_dates": "17-18 August, 2019",
            "language": Language.objects.get(name="English").pk,
            "audience_description": "Students of Hogwarts",
            "administrative_fee": "waiver",
            "scholarship_circumstances": "Bugdet cuts in Ministry of Magic",
            "travel_expences_management": "booked",
            "travel_expences_management_other": "",
            "travel_expences_agreement": True,
            "institution_restrictions": "other",
            "institution_restrictions_other": "Only for wizards",
            "public_event": "closed",
            "public_event_other": "",
            "additional_contact": "",
            "carpentries_info_source": [InfoSource.objects.first().pk],
            "carpentries_info_source_other": "",
            "user_notes": "n/c",
            "data_privacy_agreement": True,
            "code_of_conduct_agreement": True,
            "host_responsibilities": True,
            "instructor_availability": True,
            "online_inperson": "inperson",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertTrue(form.is_valid(), dict(form.errors))

    def test_institution_validation(self):
        """Make sure institution data is present, and validation
        errors are triggered for various matrix of input data."""

        # 1: selected institution from the list
        data = {
            "institution": Organization.objects.first().pk,
            "institution_other_name": "",
            "institution_other_URL": "",
            "institution_department": "School of Wizardry",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("institution", form.errors)
        self.assertNotIn("institution_other_name", form.errors)
        self.assertNotIn("institution_other_URL", form.errors)
        self.assertNotIn("institution_department", form.errors)

        # 2: institution name manually entered
        data = {
            "institution": "",
            "institution_other_name": "Hogwarts",
            "institution_other_URL": "hogwarts.uk",
            "institution_department": "School of Wizardry",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("institution", form.errors)
        self.assertNotIn("institution_other_name", form.errors)
        self.assertNotIn("institution_other_URL", form.errors)
        self.assertNotIn("institution_department", form.errors)

        # 3: no institution and no department
        data = {
            "institution": "",
            "institution_other_name": "",
            "institution_other_URL": "",
            "institution_department": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertIn("institution", form.errors)  # institution is required
        self.assertNotIn("institution_other_name", form.errors)
        self.assertNotIn("institution_other_URL", form.errors)
        self.assertNotIn("institution_department", form.errors)

        # 4: other name, but no other URL (+ no institution)
        data = {
            "institution": "",
            "institution_other_name": "Hogwarts",
            "institution_other_URL": "",
            "institution_department": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("institution", form.errors)
        self.assertIn("institution_other_name", form.errors)
        self.assertNotIn("institution_other_URL", form.errors)
        self.assertNotIn("institution_department", form.errors)

        # 5: other URL, but no other name (+ no institution)
        data = {
            "institution": "",
            "institution_other_name": "",
            "institution_other_URL": "hogwarts.uk",
            "institution_department": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("institution", form.errors)
        self.assertIn("institution_other_name", form.errors)
        self.assertNotIn("institution_other_URL", form.errors)
        self.assertNotIn("institution_department", form.errors)

        # 6: institution, other name, no other URL
        data = {
            "institution": Organization.objects.first().pk,
            "institution_other_name": "Hogwarts",
            "institution_other_URL": "",
            "institution_department": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("institution", form.errors)
        self.assertIn("institution_other_name", form.errors)
        self.assertNotIn("institution_other_URL", form.errors)
        self.assertNotIn("institution_department", form.errors)

        # 7: institution, other URL, no other name
        data = {
            "institution": Organization.objects.first().pk,
            "institution_other_name": "",
            "institution_other_URL": "hogwarts.uk",
            "institution_department": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("institution", form.errors)
        self.assertNotIn("institution_other_name", form.errors)
        self.assertIn("institution_other_URL", form.errors)
        self.assertNotIn("institution_department", form.errors)

        # 8: wrong URL format
        data = {
            "institution": "",
            "institution_other_name": "Hogwarts",
            "institution_other_URL": "wrong_url",
            "institution_department": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("institution", form.errors)
        self.assertIn("institution_other_name", form.errors)
        self.assertIn("institution_other_URL", form.errors)
        self.assertNotIn("institution_department", form.errors)

    def test_dates_validation(self):
        """Ensure preferred dates validation."""
        # 1: both empty will trigger error
        data = {
            "preferred_dates": "",
            "other_preferred_dates": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertIn("preferred_dates", form.errors)
        self.assertNotIn("other_preferred_dates", form.errors)

        # 2: either one present will work
        data = {
            "preferred_dates": "{:%Y-%m-%d}".format(date.today()),
            "other_preferred_dates": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("preferred_dates", form.errors)
        self.assertNotIn("other_preferred_dates", form.errors)

        data = {
            "preferred_dates": "",
            "other_preferred_dates": "Next weekend",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("preferred_dates", form.errors)
        self.assertNotIn("other_preferred_dates", form.errors)

        # 3: preferred date from the past
        data = {
            "preferred_dates": "2000-01-01",
            "other_preferred_dates": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertIn("preferred_dates", form.errors)
        self.assertNotIn("other_preferred_dates", form.errors)

        # 4: preferred date wrong format
        data = {
            "preferred_dates": "{:%d-%m-%Y}".format(date.today()),
            "other_preferred_dates": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertIn("preferred_dates", form.errors)
        self.assertNotIn("other_preferred_dates", form.errors)

    def test_scholarship_circumstances(self):
        """Test validation of scholarship circumstances"""
        # 1: waiver and scholarship circumstances provided
        data = {
            "administrative_fee": "waiver",
            "scholarship_circumstances": "Budget cuts",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("administrative_fee", form.errors)
        self.assertNotIn("scholarship_circumstances", form.errors)

        # 2: circumstances missing
        data = {
            "administrative_fee": "waiver",
            "scholarship_circumstances": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("administrative_fee", form.errors)
        self.assertIn("scholarship_circumstances", form.errors)

        # 3: circumstances missing, but this time it's not for a waiver
        data = {
            "administrative_fee": "nonprofit",
            "scholarship_circumstances": "",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("administrative_fee", form.errors)
        self.assertNotIn("scholarship_circumstances", form.errors)

        # 3: circumstances provided, but this time it's not for a waiver
        data = {
            "administrative_fee": "nonprofit",
            "scholarship_circumstances": "Budget cuts",
        }
        form = WorkshopRequestBaseForm(data)
        self.assertNotIn("administrative_fee", form.errors)
        self.assertIn("scholarship_circumstances", form.errors)

    def test_travel_expences_management(self):
        """Test validation of travel expences management."""
        self._test_field_other(
            Form=WorkshopRequestBaseForm,
            first_name="travel_expences_management",
            other_name="travel_expences_management_other",
            valid_first="reimbursed",
            valid_other="Local instructors don't need reimbursement",
            first_when_other="other",
        )

    def test_institution_restrictions(self):
        """Test validation of institution restrictions."""
        self._test_field_other(
            Form=WorkshopRequestBaseForm,
            first_name="institution_restrictions",
            other_name="institution_restrictions_other",
            valid_first="no_restrictions",
            valid_other="Visa required",
            first_when_other="other",
        )

    def test_public_event(self):
        """Test validation of event's openness to public."""
        self._test_field_other(
            Form=WorkshopRequestBaseForm,
            first_name="public_event",
            other_name="public_event_other",
            valid_first="public",
            valid_other="Open to conference attendees",
            first_when_other="other",
        )

    def test_instructor_availability_required(self):
        """Test requiredness of `instructor_availability` depending on selected
        preferred dates."""
        # Arrange
        data1 = {
            "preferred_dates": date.today() + timedelta(days=30),
            "other_preferred_dates": "",
            "instructor_availability": "",
        }
        data2 = {
            "preferred_dates": "",
            "other_preferred_dates": "sometime in future",
            "instructor_availability": "",
        }
        # Act
        form1 = WorkshopRequestBaseForm(data1)
        form2 = WorkshopRequestBaseForm(data2)
        # Assert
        for form in (form1, form2):
            self.assertNotIn("preferred_dates", form.errors)
            self.assertNotIn("other_preferred_dates", form.errors)
            self.assertIn("instructor_availability", form.errors)

    def test_instructor_availability_not_required(self):
        """Test `instructor_availability` not required in some circumstances."""
        # Arrange
        data1 = {
            "preferred_dates": date.today() + timedelta(days=30),
            "other_preferred_dates": "",
            "instructor_availability": "1",
        }
        data2 = {
            "preferred_dates": "",
            "other_preferred_dates": "sometime in future",
            "instructor_availability": "1",
        }
        data3 = {
            "preferred_dates": date.today() + timedelta(days=61),
            "other_preferred_dates": "",
            "instructor_availability": "",
        }
        # Act
        form1 = WorkshopRequestBaseForm(data1)
        form2 = WorkshopRequestBaseForm(data2)
        form3 = WorkshopRequestBaseForm(data3)
        # Assert
        for form in (form1, form2, form3):
            self.assertNotIn("preferred_dates", form.errors)
            self.assertNotIn("other_preferred_dates", form.errors)
            self.assertNotIn("instructor_availability", form.errors)


class TestWorkshopRequestCreateView(TestBase):
    """
    Tests membership code validation which relies on the ENFORCE_MEMBER_CODES flag.
    All other form validation is tested in the TestWorkshopRequestBaseForm class above.
    """

    INVALID_CODE_ERROR = (
        "This code is invalid. "
        "Please contact your Member Affiliate to verify your code."
    )
    MUST_ENTER_CODE = "This field is required if you selected &#x27;Yes&#x27; above."
    MUST_NOT_ENTER_CODE = (
        "This field must be empty if you selected &#x27;No&#x27; above."
    )

    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()

    def setUpMembership(self):
        Membership.objects.create(
            name="Alpha Organization",
            variant="bronze",
            agreement_start=date(2023, 8, 15),
            agreement_end=date(2024, 8, 14),
            contribution_type="financial",
            registration_code="valid123",
        )

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__affiliation_yes_code_valid(self):
        # 1: affiliation "yes" and valid code - no error
        # Arrange
        self.setUpMembership()
        data = {
            "membership_affiliation": "yes",
            "membership_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("workshop_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_CODE_ERROR)
        self.assertNotContains(rv, self.MUST_ENTER_CODE)
        self.assertNotContains(rv, self.MUST_NOT_ENTER_CODE)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__affiliation_yes_code_invalid(self):
        # 2: affiliation "yes" and invalid code - error on code
        # Arrange
        data = {
            "membership_affiliation": "yes",
            "membership_code": "invalid",
        }

        # Act
        rv = self.client.post(reverse("workshop_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, self.INVALID_CODE_ERROR)
        self.assertNotContains(rv, self.MUST_ENTER_CODE)
        self.assertNotContains(rv, self.MUST_NOT_ENTER_CODE)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__affiliation_yes_code_empty(self):
        # 3: affiliation "yes" and empty code - error on code
        # Arrange
        data = {
            "membership_affiliation": "yes",
            "membership_code": "",
        }

        # Act
        rv = self.client.post(reverse("workshop_request"), data=data)

        # Assert
        print(rv.content)
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_CODE_ERROR)
        self.assertIn(self.MUST_ENTER_CODE, rv.content.decode("utf-8"))
        self.assertNotContains(rv, self.MUST_NOT_ENTER_CODE)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__affiliation_unsure_code_valid(self):
        self.setUpMembership()
        # 4: affiliation "unsure" and valid code - no error
        # Arrange
        data = {
            "membership_affiliation": "yes",
            "membership_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("workshop_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_CODE_ERROR)
        self.assertNotContains(rv, self.MUST_ENTER_CODE)
        self.assertNotContains(rv, self.MUST_NOT_ENTER_CODE)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__affiliation_unsure_code_invalid(self):
        # 5: affiliation "unsure" and invalid code - error on code
        # Arrange
        data = {
            "membership_affiliation": "unsure",
            "membership_code": "invalid",
        }

        # Act
        rv = self.client.post(reverse("workshop_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertContains(rv, self.INVALID_CODE_ERROR)
        self.assertNotContains(rv, self.MUST_ENTER_CODE)
        self.assertNotContains(rv, self.MUST_NOT_ENTER_CODE)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__affiliation_unsure_code_empty(self):
        # 6: affiliation "unsure" and empty code - no error
        # Arrange
        data = {
            "membership_affiliation": "unsure",
            "membership_code": "",
        }

        # Act
        rv = self.client.post(reverse("workshop_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_CODE_ERROR)
        self.assertNotContains(rv, self.MUST_ENTER_CODE)
        self.assertNotContains(rv, self.MUST_NOT_ENTER_CODE)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__affiliation_no_code_not_empty(self):
        # 7: affiliation "no" and non-empty code - error on code
        # even if a valid code is entered, an error is produced
        # Arrange
        self.setUpMembership()
        data = {
            "membership_affiliation": "no",
            "membership_code": "valid123",
        }

        # Act
        rv = self.client.post(reverse("workshop_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_CODE_ERROR)
        self.assertNotContains(rv, self.MUST_ENTER_CODE)
        self.assertContains(rv, self.MUST_NOT_ENTER_CODE)

    @override_settings(FLAGS={"ENFORCE_MEMBER_CODES": [("boolean", True)]})
    def test_member_code_validation__affiliation_no_code_empty(self):
        # 8: affiliation "no" and empty code - no error
        # Arrange
        data = {
            "membership_affiliation": "no",
            "membership_code": "",
        }

        # Act
        rv = self.client.post(reverse("workshop_request"), data=data)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertNotContains(rv, self.INVALID_CODE_ERROR)
        self.assertNotContains(rv, self.MUST_ENTER_CODE)
        self.assertNotContains(rv, self.MUST_NOT_ENTER_CODE)


class TestWorkshopRequestViews(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()

        self.wr1 = WorkshopRequest.objects.create(
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
        self.wr2 = WorkshopRequest.objects.create(
            state="d",
            personal="Harry",
            family="Potter",
            email="harry@potter.com",
            institution_other_name="Hogwarts",
            location="Scotland",
            country="GB",
            preferred_dates=None,
            other_preferred_dates="soon",
            language=Language.objects.get(name="English"),
            audience_description="Students of Hogwarts",
            administrative_fee="forprofit",
            scholarship_circumstances="",
            travel_expences_management="reimbursed",
            travel_expences_management_other="",
            institution_restrictions="",
            institution_restrictions_other="Visa required",
            carpentries_info_source_other="",
            user_notes="",
        )

    def test_pending_requests_list(self):
        rv = self.client.get(reverse("all_workshoprequests"))
        self.assertIn(self.wr1, rv.context["requests"])
        self.assertNotIn(self.wr2, rv.context["requests"])

    def test_discarded_requests_list(self):
        rv = self.client.get(reverse("all_workshoprequests") + "?state=d")
        self.assertNotIn(self.wr1, rv.context["requests"])
        self.assertIn(self.wr2, rv.context["requests"])

    def test_set_state_pending_request_view(self):
        rv = self.client.get(
            reverse("workshoprequest_set_state", args=[self.wr1.pk, "discarded"])
        )
        self.assertEqual(rv.status_code, 302)
        self.wr1.refresh_from_db()
        self.assertEqual(self.wr1.state, "d")

    def test_set_state_discarded_request_view(self):
        rv = self.client.get(
            reverse("workshoprequest_set_state", args=[self.wr2.pk, "discarded"])
        )
        self.assertEqual(rv.status_code, 302)
        self.wr2.refresh_from_db()
        self.assertEqual(self.wr2.state, "d")

    def test_pending_request_accept(self):
        rv = self.client.get(
            reverse("workshoprequest_set_state", args=[self.wr1.pk, "accepted"])
        )
        self.assertEqual(rv.status_code, 302)

    def test_pending_request_accepted_with_event(self):
        """Ensure a backlink from Event to WorkshopRequest that created the
        event exists after ER is accepted."""
        data = {
            "slug": "2018-10-28-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [1],
        }
        rv = self.client.post(
            reverse("workshoprequest_accept_event", args=[self.wr1.pk]), data
        )
        self.assertEqual(rv.status_code, 302)
        request = Event.objects.get(slug="2018-10-28-test-event").workshoprequest
        self.assertEqual(request, self.wr1)

    def test_discarded_request_not_accepted_with_event(self):
        rv = self.client.get(
            reverse("workshoprequest_accept_event", args=[self.wr2.pk])
        )
        self.assertEqual(rv.status_code, 404)

    def test_pending_request_discard(self):
        rv = self.client.get(
            reverse("workshoprequest_set_state", args=[self.wr1.pk, "discarded"]),
            follow=True,
        )
        self.assertEqual(rv.status_code, 200)

    def test_discarded_request_discard(self):
        rv = self.client.get(
            reverse("workshoprequest_set_state", args=[self.wr2.pk, "discarded"]),
            follow=True,
        )
        self.assertEqual(rv.status_code, 200)

    def test_discarded_request_reopened(self):
        self.wr1.state = "a"
        self.wr1.save()
        self.client.get(
            reverse("workshoprequest_set_state", args=[self.wr1.pk, "pending"]),
            follow=True,
        )
        self.wr1.refresh_from_db()
        self.assertEqual(self.wr1.state, "p")

    def test_accepted_request_reopened(self):
        self.assertEqual(self.wr2.state, "d")
        self.client.get(
            reverse("workshoprequest_set_state", args=[self.wr2.pk, "pending"]),
            follow=True,
        )
        self.wr2.refresh_from_db()
        self.assertEqual(self.wr2.state, "p")

    def test_list_no_comments(self):
        """Regression for #1435: missing "comment" field displayed on "all
        workshops" page.

        https://github.com/swcarpentry/amy/issues/1435
        """

        # make sure the `string_if_invalid` is not empty
        self.assertTrue(settings.TEMPLATES[0]["OPTIONS"]["string_if_invalid"])

        rv = self.client.get(reverse("all_workshoprequests"))

        # some objects available in the page
        self.assertNotEqual(len(rv.context["requests"]), 0)

        # no string_if_invalid found in the page
        invalid = settings.TEMPLATES[0]["OPTIONS"]["string_if_invalid"]
        self.assertNotIn(invalid, rv.content.decode("utf-8"))


class TestAcceptingWorkshopRequest(TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()

        self.wr1 = WorkshopRequest.objects.create(
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

        self.url = reverse("workshoprequest_accept_event", args=[self.wr1.pk])

    def test_page_context(self):
        """Ensure proper objects render in the page."""
        rv = self.client.get(self.url)
        self.assertIn("form", rv.context)
        self.assertIn("object", rv.context)  # this is our request
        form = rv.context["form"]
        wr = rv.context["object"]
        self.assertEqual(wr, self.wr1)
        self.assertTrue(isinstance(form, EventCreateForm))

    def test_state_changed(self):
        """Ensure request's state is changed after accepting."""
        self.assertTrue(self.wr1.state == "p")
        data = {
            "slug": "2018-10-28-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [1],
        }
        rv = self.client.post(self.url, data)
        self.assertEqual(rv.status_code, 302)
        self.wr1.refresh_from_db()
        self.assertTrue(self.wr1.state == "a")

    def test_host_task_created(self):
        """Ensure a host task is created when a person submitting the request
        already is in our database."""

        # Harry matched as a submitted for self.wr1, and he has no tasks so far
        self.assertEqual(self.wr1.host(), self.harry)
        self.assertFalse(self.harry.task_set.all())

        # create event from that workshop request
        data = {
            "slug": "2019-08-18-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "administrator": Organization.objects.administrators().first().id,
            "tags": [1],
        }
        rv = self.client.post(self.url, data)
        self.assertEqual(rv.status_code, 302)
        event = Event.objects.get(slug="2019-08-18-test-event")

        # check if Harry gained a task
        Task.objects.get(
            person=self.harry, event=event, role=Role.objects.get(name="host")
        )


class TestAcceptWorkshopRequestAddsEmailAction(FakeRedisTestCaseMixin, TestBase):
    def setUp(self):
        super().setUp()
        self._setUpRoles()
        self._setUpUsersAndLogin()
        # we're missing some tags
        Tag.objects.bulk_create(
            [
                Tag(name="automated-email", priority=0),
                Tag(name="SWC", priority=10),
                Tag(name="DC", priority=20),
                Tag(name="LC", priority=30),
                Tag(name="TTT", priority=40),
            ]
        )

        self.wr1 = WorkshopRequest.objects.create(
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

        template1 = EmailTemplate.objects.create(
            slug="sample-template1",
            subject="Welcome to {{ site.name }}",
            to_header="recipient@address.com",
            from_header="test@address.com",
            cc_header="copy@example.org",
            bcc_header="bcc@example.org",
            reply_to_header="{{ reply_to }}",
            body_template="Sample text.",
        )
        self.trigger1 = Trigger.objects.create(
            action="week-after-workshop-completion",
            template=template1,
        )

        self.url = reverse("workshoprequest_accept_event", args=[self.wr1.pk])

        # save scheduler and connection data
        self._saved_scheduler = extrequests.views.scheduler
        self._saved_redis_connection = extrequests.views.redis_connection
        # overwrite them
        extrequests.views.scheduler = self.scheduler
        extrequests.views.redis_connection = self.connection

    def tearDown(self):
        super().tearDown()
        extrequests.views.scheduler = self._saved_scheduler
        extrequests.views.redis_connection = self._saved_redis_connection

    def test_jobs_created(self):
        data = {
            "slug": "xxxx-xx-xx-test-event",
            "host": Organization.objects.first().pk,
            "sponsor": Organization.objects.first().pk,
            "administrator": Organization.objects.get(domain="self-organized").pk,
            "start": date.today() + timedelta(days=7),
            "end": date.today() + timedelta(days=8),
            "tags": Tag.objects.filter(name__in=["automated-email", "LC"]).values_list(
                "pk", flat=True
            ),
        }

        # no jobs scheduled
        rqjobs_pre = RQJob.objects.all()
        self.assertQuerysetEqual(rqjobs_pre, [])

        # send data in
        rv = self.client.post(self.url, data, follow=True)
        self.assertEqual(rv.status_code, 200)
        event = Event.objects.get(slug="xxxx-xx-xx-test-event")
        request = event.workshoprequest
        self.assertEqual(request, self.wr1)

        # 1 job created
        rqjobs_post = RQJob.objects.all()
        self.assertEqual(len(rqjobs_post), 1)

        # ensure the job ids are mentioned in the page output
        content = rv.content.decode("utf-8")
        for job in rqjobs_post:
            self.assertIn(job.job_id, content)

        # ensure the job is for PostWorkshopAction
        rqjobs_post[0].trigger = self.trigger1
