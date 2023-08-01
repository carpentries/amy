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
            rv, "Your Get Involved submission will be evaluated within 7-10 days."
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


class TestGetInvolvedCreateViewPermissions(TestBase):
    def setUp(self):
        super().setUp()
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
        self.demo, _ = TrainingRequirement.objects.get_or_create(name="Demo")
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

    def test_cannot_create_if_not_logged_in(self):
        self.client.logout()

        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_add"))
        rv_post = self.client.post(reverse("getinvolved_add"), data)

        # Assert
        self.assertEqual(rv_get.status_code, 302)
        self.assertEqual(rv_post.status_code, 302)

    def test_cannot_create_if_not_evaluated_yet(self):
        # Arrange
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 1),
            url="https://example.org",
            state="n",
        )

        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv = self.client.post(reverse("getinvolved_add"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "getinvolved_add")
        self.assertContains(rv, "You may not create another submission")
        # confirm that no TrainingProgress was created
        self.assertEqual(len(TrainingProgress.objects.all()), 1)

    def test_cannot_create_if_passed(self):
        # Arrange
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 1),
            url="https://example.org",
            state="p",
        )

        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv = self.client.post(reverse("getinvolved_add"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "getinvolved_add")
        self.assertContains(rv, "You may not create another submission")
        # confirm that no TrainingProgress was created
        self.assertEqual(len(TrainingProgress.objects.all()), 1)

    def test_cannot_create_if_failed(self):
        # Arrange
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 1),
            url="https://example.org",
            state="p",
        )

        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv = self.client.post(reverse("getinvolved_add"), data, follow=True)

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "getinvolved_add")
        self.assertContains(rv, "You may not create another submission")
        # confirm that no TrainingProgress was created
        self.assertEqual(len(TrainingProgress.objects.all()), 1)

    def test_can_create_if_asked_to_repeat(self):
        # Arrange
        TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 1),
            url="https://example.org",
            state="a",
        )

        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_add"))
        rv_post = self.client.post(reverse("getinvolved_add"), data, follow=True)

        # Assert
        self.assertEqual(rv_get.status_code, 200)
        self.assertEqual(rv_post.status_code, 200)
        self.assertEqual(rv_post.resolver_match.view_name, "training-progress")
        self.assertContains(
            rv_post,
            "Your Get Involved submission will be evaluated within 7-10 days.",
        )
        # confirm that the TrainingProgress was created
        self.assertEqual(len(TrainingProgress.objects.all()), 2)

    def test_trainee_cannot_set_type_or_state(self):
        # Arrange

        data = {
            "requirement": self.demo,
            "state": "p",
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
            rv, "Your Get Involved submission will be evaluated within 7-10 days."
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


class TestGetInvolvedUpdateViewPermissions(TestBase):
    def setUp(self):
        super().setUp()
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
        self.demo, _ = TrainingRequirement.objects.get_or_create(name="Demo")
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

    def test_cannot_update_if_not_logged_in(self):
        self.client.logout()

        # Arrange
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 1),
            url="https://example.org",
            state="n",
        )
        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_update", args=[progress.pk]))
        rv_post = self.client.post(
            reverse("getinvolved_update", args=[progress.pk]), data
        )

        # Assert
        self.assertEqual(rv_get.status_code, 302)
        self.assertEqual(rv_post.status_code, 302)

    def test_cannot_update_other_trainees_submission(self):
        # Arrange
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 1),
            url="https://example.org",
            state="n",
        )
        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_update", args=[progress.pk]))
        rv_post = self.client.post(
            reverse("getinvolved_update", args=[progress.pk]), data, follow=True
        )

        # Assert
        self.assertEqual(rv_get.status_code, 403)
        self.assertEqual(rv_post.status_code, 403)

    def test_cannot_update_progress_of_other_type(self):
        # Arrange
        progress = TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.demo,
            date=date(2023, 7, 31),
            state="n",
        )
        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_update", args=[progress.pk]))
        rv_post = self.client.post(
            reverse("getinvolved_update", args=[progress.pk]), data, follow=True
        )

        # Assert
        self.assertEqual(rv_get.status_code, 403)
        self.assertEqual(rv_post.status_code, 403)

    def test_cannot_update_evaluated_progress(self):
        # Arrange
        progress = TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 31),
            state="a",
        )
        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_update", args=[progress.pk]))
        rv_post = self.client.post(
            reverse("getinvolved_update", args=[progress.pk]), data, follow=True
        )

        # Assert
        self.assertEqual(rv_get.status_code, 403)
        self.assertEqual(rv_post.status_code, 403)

    def test_cannot_update_non_existent_progress(self):
        # Arrange
        id = 1000
        data = {
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_update", args=[id]))
        rv_post = self.client.post(
            reverse("getinvolved_update", args=[id]), data, follow=True
        )

        # Assert
        self.assertEqual(rv_get.status_code, 403)
        self.assertEqual(rv_post.status_code, 403)

    def test_trainee_cannot_set_type_or_state(self):
        # Arrange
        progress = TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 31),
            state="n",
        )
        data = {
            "requirement": self.demo,
            "state": "p",
            "involvement_type": self.github_contribution.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv = self.client.post(
            reverse("getinvolved_update", args=[progress.pk]), data, follow=True
        )

        # Assert
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.resolver_match.view_name, "training-progress")
        self.assertContains(
            rv, "Your Get Involved submission was updated successfully."
        )
        got = list(
            TrainingProgress.objects.values_list(
                "state", "trainee", "url", "requirement", "involvement_type", "date"
            )
        )
        expected = [
            (  # date changed but not state or requirement
                "n",
                self.admin.pk,
                "https://example.org",
                self.get_involved.pk,
                self.github_contribution.pk,
                date(2023, 7, 27),
            )
        ]
        self.assertEqual(got, expected)


class TestGetInvolvedDeleteViewPermissions(TestBase):
    def setUp(self):
        super().setUp()
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
        self.demo, _ = TrainingRequirement.objects.get_or_create(name="Demo")
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

    def test_cannot_delete_if_not_logged_in(self):
        self.client.logout()

        # Arrange
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 1),
            url="https://example.org",
            state="n",
        )

        # Act
        rv_post = self.client.post(reverse("getinvolved_delete", args=[progress.pk]))

        # Assert
        self.assertEqual(rv_post.status_code, 302)

    def test_cannot_delete_other_trainees_submission(self):
        # Arrange
        progress = TrainingProgress.objects.create(
            trainee=self.spiderman,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 31),
            url="https://example.org",
            state="n",
        )

        # Act
        rv = self.client.post(reverse("getinvolved_delete", args=[progress.pk]))

        # Assert
        self.assertEqual(rv.status_code, 403)

    def test_cannot_delete_progress_of_other_type(self):
        # Arrange
        progress = TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.demo,
            date=date(2023, 7, 31),
            state="n",
        )

        # Act
        rv = self.client.post(reverse("getinvolved_delete", args=[progress.pk]))

        # Assert
        self.assertEqual(rv.status_code, 403)

    def test_cannot_delete_evaluated_progress(self):
        # Arrange
        progress = TrainingProgress.objects.create(
            trainee=self.admin,
            requirement=self.get_involved,
            involvement_type=self.github_contribution,
            date=date(2023, 7, 31),
            state="a",
        )

        # Act
        rv = self.client.post(reverse("getinvolved_delete", args=[progress.pk]))

        # Assert
        self.assertEqual(rv.status_code, 403)

    def test_cannot_delete_non_existent_progress(self):
        # Arrange
        id = 1000

        # Act
        rv = self.client.post(reverse("getinvolved_delete", args=[id]))

        # Assert
        self.assertEqual(rv.status_code, 403)
