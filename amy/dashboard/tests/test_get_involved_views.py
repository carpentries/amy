from datetime import date

from django.urls import reverse

from trainings.models import Involvement
from workshops.models import TrainingProgress, TrainingRequirement
from workshops.tests.base import TestBase


class TestGetInvolvedCreateView(TestBase):
    def setUp(self):
        super()._setUpUsersAndLogin()
        self._setUpRoles()
        self._setUpTags()

        self.get_involved, _ = TrainingRequirement.objects.get_or_create(
            name="Get Involved",
            defaults={
                "url_required": False,
                "event_required": False,
                "involvement_required": True,
            },
        )
        self.github_contribution, _ = Involvement.objects.get_or_create(
            name="GitHub Contribution",
            defaults={
                "display_name": "GitHub Contribution",
                "url_required": True,
                "date_required": True,
            },
        )
        self.involvement_to_be_archived, _ = Involvement.objects.get_or_create(
            name="To be archived",
            defaults={
                "display_name": "To be archived",
                "url_required": True,
                "date_required": True,
            },
        )
        self.involvement_other, _ = Involvement.objects.get_or_create(
            name="Other",
            defaults={
                "display_name": "Other",
                "notes_required": True,
            },
        )

    def test_create_view_loads(self):
        # Act
        rv = self.client.get(reverse("getinvolved_add"))

        # Assert
        self.assertEqual(rv.status_code, 200)

    def test_create_view_does_not_show_archived_involvements(self):
        # Arrange
        self.involvement_to_be_archived.archive()

        # Act
        rv = self.client.get(reverse("getinvolved_add"))

        # Assert
        self.assertEqual(rv.status_code, 200)
        choices = [
            c[0].instance.pk
            for c in rv.context["form"].fields["involvement_type"].choices
        ]
        self.assertEqual(
            choices, [self.github_contribution.pk, self.involvement_other.pk]
        )

    def test_create_view_does_not_show_admin_fields(self):
        # Act
        rv = self.client.get(reverse("getinvolved_add"))

        # Assert
        self.assertEqual(rv.status_code, 200)
        expected_fields = {"involvement_type", "date", "url", "trainee_notes"}
        self.assertSetEqual(set(rv.context["form"].fields.keys()), expected_fields)

    def test_create_view_works(self):
        # Arrange
        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv = self.client.post(reverse("getinvolved_add"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "training-progress")
        self.assertContains(
            rv, "Your Get Involved submission will be reviewed within 7-10 days."
        )
        got = list(
            TrainingProgress.objects.values_list(
                "state", "trainee", "url", "requirement", "involvement_type", "date"
            )
        )
        expected = [
            (
                "n",
                self.admin.pk,
                "https://example.org",
                self.get_involved.pk,
                self.github_contribution.pk,
                date(2023, 7, 27),
            )
        ]
        self.assertEqual(got, expected)

    def test_create_view_submission_invalid_notes(self):
        """Test that errors relating to notes/trainee_notes fields are
        handled correctly."""

        # Arrange
        data = {
            "involvement_type": self.involvement_other.pk,
            "date": "2023-07-27",
        }

        # Act
        rv = self.client.post(reverse("getinvolved_add"), data, follow=True)

        # Assert
        # if "notes" field error is not excluded, a server error will occur
        # as there is no "notes" field on the form
        # so a status code 200 means it has been excluded correctly
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "getinvolved_add")
        # check that "trainee_notes" field error IS displayed
        self.assertContains(
            rv,
            'This field is required for activity "Other".',
            html=True,
        )
        # check that "notes" field error IS NOT displayed
        self.assertNotContains(
            rv,
            'This field is required for activity "Other" '
            "if there are no notes from the trainee.",
            html=True,
        )
        # confirm that no TrainingProgress was created
        self.assertEqual(len(TrainingProgress.objects.all()), 0)


class TestGetInvolvedUpdateView(TestBase):
    def setUp(self):
        super()._setUpUsersAndLogin()

        self.get_involved, _ = TrainingRequirement.objects.get_or_create(
            name="Get Involved",
            defaults={
                "url_required": False,
                "event_required": False,
                "involvement_required": True,
            },
        )
        self.involvement, _ = Involvement.objects.get_or_create(
            name="GitHub Contribution",
            defaults={
                "display_name": "GitHub Contribution",
                "url_required": True,
                "date_required": True,
            },
        )

        self.progress = TrainingProgress.objects.create(
            trainee=self.admin,
            state="n",
            requirement=self.get_involved,
            involvement_type=self.involvement,
            url="https://example.org",
            date=date(2023, 7, 27),
        )

    def test_edit_view_loads(self):
        # Act
        rv = self.client.get(reverse("getinvolved_update", args=[self.progress.pk]))

        # Assert
        self.assertEqual(rv.status_code, 200)


class TestGetInvolvedDeleteView(TestBase):
    def setUp(self):
        super()._setUpUsersAndLogin()

        self.get_involved, _ = TrainingRequirement.objects.get_or_create(
            name="Get Involved",
            defaults={
                "url_required": False,
                "event_required": False,
                "involvement_required": True,
            },
        )
        self.involvement, _ = Involvement.objects.get_or_create(
            name="GitHub Contribution",
            defaults={
                "display_name": "GitHub Contribution",
                "url_required": True,
                "date_required": True,
            },
        )
        self.progress = TrainingProgress.objects.create(
            trainee=self.admin,
            state="n",
            requirement=self.get_involved,
            involvement_type=self.involvement,
            url="https://example.org",
            date=date(2023, 7, 27),
        )

    def test_delete_view_get_request_not_allowed(self):
        # Act
        rv = self.client.get(reverse("getinvolved_delete", args=[self.progress.pk]))

        # Assert
        self.assertEqual(rv.status_code, 405)

    def test_delete_view_works(self):
        # Act
        rv = self.client.post(
            reverse("getinvolved_delete", args=[self.progress.pk]), follow=True
        )

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "training-progress")
        self.assertEqual(set(TrainingProgress.objects.all()), set())
