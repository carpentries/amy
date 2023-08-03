from datetime import date

from django.urls import reverse

from trainings.models import Involvement
from workshops.models import Person, TrainingProgress, TrainingRequirement
from workshops.tests.base import TestBase, consent_to_all_required_consents


class TestGetInvolvedViewBase(TestBase):
    def setUp(self):
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
        self.involvement, _ = Involvement.objects.get_or_create(
            name="GitHub Contribution",
            defaults={
                "display_name": "GitHub Contribution",
                "url_required": True,
                "date_required": True,
            },
        )

        # set up and log in as a trainee
        self.user = Person.objects.create_user(
            username="trainee_alice",
            personal="Alice",
            family="Trainee",
            email="alice_trainee@example.com",
            password="password",
        )
        consent_to_all_required_consents(self.user)
        self.client.login(username="trainee_alice", password="password")


class TestGetInvolvedCreateView(TestGetInvolvedViewBase):
    def setUp(self):
        super().setUp()
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
        self.assertEqual(choices, [self.involvement.pk, self.involvement_other.pk])

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
            "involvement_type": self.involvement.pk,
            "url": "https://github.com/carpentries",
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
                self.user.pk,
                "https://example.org",
                self.get_involved.pk,
                self.involvement.pk,
                date(2023, 7, 27),
            )
        ]
        self.assertEqual(got, expected)

    def test_cannot_create_if_not_logged_in(self):
        self.client.logout()

        data = {
            "involvement_type": self.involvement.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_add"))
        rv_post = self.client.post(reverse("getinvolved_add"), data)

        # Assert
        self.assertEqual(rv_get.status_code, 302)
        self.assertEqual(rv_post.status_code, 302)
        # cannot check by assertRedirect because there's additional `?next`
        # parameter
        self.assertTrue(rv_get.url.startswith(reverse("login")))
        self.assertTrue(rv_post.url.startswith(reverse("login")))

    def test_trainee_cannot_set_type_or_state(self):
        # Arrange

        demo, _ = TrainingRequirement.objects.get_or_create(name="Demo")
        data = {
            "requirement": demo,
            "state": "p",
            "involvement_type": self.involvement.pk,
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
                self.user.pk,
                "https://github.com/carpentries",
                self.get_involved.pk,
                self.involvement.pk,
                date(2023, 7, 27),
            )
        ]
        self.assertEqual(got, expected)


class TestGetInvolvedUpdateView(TestGetInvolvedViewBase):
    def setUp(self):
        super().setUp()

        self.progress = TrainingProgress.objects.create(
            trainee=self.user,
            state="n",
            requirement=self.get_involved,
            involvement_type=self.involvement,
            url="https://example.org",
            date=date(2023, 7, 27),
        )

    def test_update_view_loads(self):
        # Act
        rv = self.client.get(reverse("getinvolved_update", args=[self.progress.pk]))

        # Assert
        self.assertEqual(rv.status_code, 200)

    def test_update_view_works(self):
        # Arrange
        data = {
            "involvement_type": self.involvement.pk,
            "url": "https://second-example.org",
            "date": "2023-08-03",
        }

        # Act
        rv = self.client.post(
            reverse("getinvolved_update", args=[self.progress.pk]), data, follow=True
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
            (
                "n",
                self.user.pk,
                "https://second-example.org",
                self.get_involved.pk,
                self.involvement.pk,
                date(2023, 8, 3),
            )
        ]
        self.assertEqual(got, expected)

    def test_cannot_update_if_not_logged_in(self):
        self.client.logout()

        # Arrange
        data = {
            "involvement_type": self.involvement.pk,
            "url": "https://second-example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_update", args=[self.progress.pk]))
        rv_post = self.client.post(
            reverse("getinvolved_update", args=[self.progress.pk]), data
        )

        # Assert
        self.assertEqual(rv_get.status_code, 302)
        self.assertEqual(rv_post.status_code, 302)
        # cannot check by assertRedirect because there's additional `?next`
        # parameter
        self.assertTrue(rv_get.url.startswith(reverse("login")))
        self.assertTrue(rv_post.url.startswith(reverse("login")))

    def test_cannot_update_evaluated_progress(self):
        # Arrange
        self.progress.state = "p"
        self.progress.save()

        data = {
            "involvement_type": self.involvement.pk,
            "url": "https://second-example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_update", args=[self.progress.pk]))
        rv_post = self.client.post(
            reverse("getinvolved_update", args=[self.progress.pk]), data, follow=True
        )

        # Assert
        self.assertEqual(rv_get.status_code, 404)
        self.assertEqual(rv_post.status_code, 404)

    def test_cannot_update_progress_of_other_type(self):
        # Arrange
        demo, _ = TrainingRequirement.objects.get_or_create(name="Demo")
        progress = TrainingProgress.objects.create(
            trainee=self.user,
            requirement=demo,
            date=date(2023, 7, 31),
            state="n",
        )
        data = {
            "involvement_type": self.involvement.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_update", args=[progress.pk]))
        rv_post = self.client.post(
            reverse("getinvolved_update", args=[progress.pk]), data, follow=True
        )

        # Assert
        self.assertEqual(rv_get.status_code, 404)
        self.assertEqual(rv_post.status_code, 404)

    def test_cannot_update_non_existent_progress(self):
        # Arrange
        id = 1000
        data = {
            "involvement_type": self.involvement.pk,
            "url": "https://example.org",
            "date": "2023-07-27",
        }

        # Act
        rv_get = self.client.get(reverse("getinvolved_update", args=[id]))
        rv_post = self.client.post(
            reverse("getinvolved_update", args=[id]), data, follow=True
        )

        # Assert
        self.assertEqual(rv_get.status_code, 404)
        self.assertEqual(rv_post.status_code, 404)

    def test_trainee_cannot_set_type_or_state(self):
        # Arrange
        demo, _ = TrainingRequirement.objects.get_or_create(name="Demo")
        data = {
            "requirement": demo,
            "state": "p",
            "involvement_type": self.involvement.pk,
            "url": "https://second-example.org",
            "date": "2023-07-27",
        }

        # Act
        rv = self.client.post(
            reverse("getinvolved_update", args=[self.progress.pk]), data, follow=True
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
                self.user.pk,
                "https://second-example.org",
                self.get_involved.pk,
                self.involvement.pk,
                date(2023, 7, 27),
            )
        ]
        self.assertEqual(got, expected)


class TestGetInvolvedDeleteView(TestGetInvolvedViewBase):
    def setUp(self):
        super().setUp()

        self.progress = TrainingProgress.objects.create(
            trainee=self.user,
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

    def test_cannot_delete_if_not_logged_in(self):
        # Arrange
        self.client.logout()

        # Act
        rv_post = self.client.post(
            reverse("getinvolved_delete", args=[self.progress.pk])
        )

        # Assert
        self.assertEqual(rv_post.status_code, 302)
        # cannot check by assertRedirect because there's additional `?next`
        # parameter
        self.assertTrue(rv_post.url.startswith(reverse("login")))

    def test_cannot_delete_other_trainees_submission(self):
        # Arrange
        other_trainee = Person.objects.create(
            personal="Bob", family="Trainee", email="bob_trainee@example.com"
        )

        progress = TrainingProgress.objects.create(
            trainee=other_trainee,
            requirement=self.get_involved,
            involvement_type=self.involvement,
            date=date(2023, 7, 31),
            url="https://example.org",
            state="n",
        )

        # Act
        rv = self.client.post(reverse("getinvolved_delete", args=[progress.pk]))

        # Assert
        self.assertEqual(rv.status_code, 404)

    def test_cannot_delete_progress_of_other_type(self):
        # Arrange
        demo, _ = TrainingRequirement.objects.get_or_create(name="Demo")
        progress = TrainingProgress.objects.create(
            trainee=self.user,
            requirement=demo,
            date=date(2023, 7, 31),
            state="n",
        )

        # Act
        rv = self.client.post(reverse("getinvolved_delete", args=[progress.pk]))

        # Assert
        self.assertEqual(rv.status_code, 404)

    def test_cannot_delete_evaluated_progress(self):
        # Arrange
        self.progress.state = "a"
        self.progress.save()

        # Act
        rv = self.client.post(reverse("getinvolved_delete", args=[self.progress.pk]))

        # Assert
        self.assertEqual(rv.status_code, 404)

    def test_cannot_delete_non_existent_progress(self):
        # Arrange
        id = 1000

        # Act
        rv = self.client.post(reverse("getinvolved_delete", args=[id]))

        # Assert
        self.assertEqual(rv.status_code, 404)
