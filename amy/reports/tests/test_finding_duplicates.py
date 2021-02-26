from datetime import date, datetime, timedelta

from django.utils import timezone
from django.urls import reverse

from workshops.models import Person
from workshops.tests.base import TestBase


class TestEmptyDuplicates(TestBase):
    """Tests to return empty context variables when no matches found."""

    def setUp(self):
        self._setUpUsersAndLogin()

        self.harry = Person.objects.create(
            personal="Harry",
            family="Potter",
            username="potter_harry",
            email="hp@hogwart.edu",
        )
        self.kira = Person.objects.create(
            personal="Light",
            family="Yagami",
            username="light_yagami",
            email="ly@hogwart.edu",
        )
        self.batman = Person.objects.create(
            personal="Bruce",
            family="Wayne",
            username="bruce_wayne",
            email="batman@waynecorp.com",
        )
        self.ironman = Person.objects.create(
            personal="Tony",
            family="Stark",
            username="tony_stark",
            email="ironman@starkindustries.com",
        )

        self.url = reverse("duplicate_persons")

    def test_switched_names_persons(self):
        """Ensure none of the above persons are in `switched_persons`."""
        rv = self.client.get(self.url)
        switched = rv.context["switched_persons"]
        self.assertNotIn(self.harry, switched)
        self.assertNotIn(self.kira, switched)
        self.assertNotIn(self.batman, switched)
        self.assertNotIn(self.ironman, switched)

    def test_duplicate_persons(self):
        """Ensure none of the above persons are in `duplicate_persons`."""
        rv = self.client.get(self.url)
        switched = rv.context["duplicate_persons"]
        self.assertNotIn(self.harry, switched)
        self.assertNotIn(self.kira, switched)
        self.assertNotIn(self.batman, switched)
        self.assertNotIn(self.ironman, switched)


class TestFindingDuplicates(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

        self.harry = Person.objects.create(
            personal="Harry",
            family="Potter",
            username="potter_harry",
            email="hp@hogwart.edu",
        )
        self.potter = Person.objects.create(
            personal="Potter",
            family="Harry",
            username="harry_potter",
            email="hp+1@hogwart.edu",
        )
        self.ron = Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="weasley_ron",
            email="rw@hogwart.edu",
        )
        self.ron2 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="weasley_ron_2",
            email="rw+1@hogwart.edu",
        )

        self.url = reverse("duplicate_persons")

    def test_switched_names_persons(self):
        rv = self.client.get(self.url)
        switched = rv.context["switched_persons"]
        self.assertIn(self.harry, switched)
        self.assertIn(self.potter, switched)
        self.assertNotIn(self.ron, switched)
        self.assertNotIn(self.ron2, switched)

    def test_duplicate_persons(self):
        rv = self.client.get(self.url)
        duplicated = rv.context["duplicate_persons"]
        self.assertIn(self.ron, duplicated)
        self.assertIn(self.ron2, duplicated)
        self.assertNotIn(self.harry, duplicated)
        self.assertNotIn(self.potter, duplicated)


class TestFindingReviewedDuplicates(TestBase):
    def setUp(self):
        self._setUpUsersAndLogin()

        self.harry = Person.objects.create(
            personal="Harry",
            family="Potter",
            username="potter_harry",
            email="hp@hogwart.edu",
        )
        self.potter = Person.objects.create(
            personal="Potter",
            family="Harry",
            username="harry_potter",
            email="hp+1@hogwart.edu",
        )
        self.ron = Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="weasley_ron",
            email="rw@hogwart.edu",
        )
        self.ron2 = Person.objects.create(
            personal="Ron",
            family="Weasley",
            username="weasley_ron_2",
            email="rw+1@hogwart.edu",
        )

        self.url = reverse("duplicate_persons")
        self.review_url = reverse("review_duplicate_persons")

    def test_finding_unreviewed_duplicates(self):
        rv = self.client.get(self.url)
        switched = rv.context["switched_persons"]
        duplicates = rv.context["duplicate_persons"]

        self.assertEqual(self.harry.duplication_reviewed_on, None)
        self.assertEqual(self.potter.duplication_reviewed_on, None)
        self.assertEqual(self.ron.duplication_reviewed_on, None)
        self.assertEqual(self.ron2.duplication_reviewed_on, None)

        self.assertIn(self.harry, switched)
        self.assertIn(self.potter, switched)
        self.assertNotIn(self.ron, switched)
        self.assertNotIn(self.ron2, switched)

        self.assertIn(self.ron, duplicates)
        self.assertIn(self.ron2, duplicates)
        self.assertNotIn(self.harry, duplicates)
        self.assertNotIn(self.potter, duplicates)

    def test_not_finding_reviewed_duplicates(self):
        """Ensure records with `last_changed_at` timestamp close to their
        `duplication_reviewed_on` timestamp don't show up in the results."""

        # modify duplication_reviewed_on to point to the
        # same timestamp (or very close) that last_updated_at will
        # after save() so that these records don't show up in results
        review_date = timezone.now()

        self.harry.duplication_reviewed_on = review_date
        self.harry.save()
        self.potter.duplication_reviewed_on = review_date
        self.potter.save()
        self.ron.duplication_reviewed_on = review_date
        self.ron.save()
        self.ron2.duplication_reviewed_on = review_date
        self.ron2.save()

        rv = self.client.get(self.url)
        switched = rv.context["switched_persons"]
        duplicates = rv.context["duplicate_persons"]

        self.assertNotIn(self.harry, switched)
        self.assertNotIn(self.potter, switched)
        self.assertNotIn(self.ron, switched)
        self.assertNotIn(self.ron2, switched)

        self.assertNotIn(self.ron, duplicates)
        self.assertNotIn(self.ron2, duplicates)
        self.assertNotIn(self.harry, duplicates)
        self.assertNotIn(self.potter, duplicates)

    def test_finding_duplicates_changed_soon_after_reviewed(self):
        # make sure after changing the timestamp difference between
        # `last_updated_at` and `duplication_reviewed_on` to couple minutes,
        # the records show up
        review_date = timezone.now() - timedelta(minutes=2)

        self.harry.duplication_reviewed_on = review_date
        self.harry.save()
        self.potter.duplication_reviewed_on = review_date
        self.potter.save()
        self.ron.duplication_reviewed_on = review_date
        self.ron.save()
        self.ron2.duplication_reviewed_on = review_date
        self.ron2.save()

        rv = self.client.get(self.url)
        switched = rv.context["switched_persons"]
        duplicates = rv.context["duplicate_persons"]

        self.assertIn(self.harry, switched)
        self.assertIn(self.potter, switched)
        self.assertNotIn(self.ron, switched)
        self.assertNotIn(self.ron2, switched)

        self.assertIn(self.ron, duplicates)
        self.assertIn(self.ron2, duplicates)
        self.assertNotIn(self.harry, duplicates)
        self.assertNotIn(self.potter, duplicates)

    def test_finding_reviewed_changed_duplicates(self):
        # modify last_updated_at and duplication_reviewed_on
        # so that these records don't show up in results
        change_timestamp = timezone.now()
        review_date = change_timestamp - timedelta(days=1)

        self.harry.duplication_reviewed_on = review_date
        self.harry.last_updated_at = change_timestamp
        self.harry.save()
        self.potter.duplication_reviewed_on = review_date
        self.potter.last_updated_at = change_timestamp
        self.potter.save()
        self.ron.duplication_reviewed_on = review_date
        self.ron.last_updated_at = change_timestamp
        self.ron.save()
        self.ron2.duplication_reviewed_on = review_date
        self.ron2.last_updated_at = change_timestamp
        self.ron2.save()

        rv = self.client.get(self.url)
        switched = rv.context["switched_persons"]
        duplicates = rv.context["duplicate_persons"]

        self.assertIn(self.harry, switched)
        self.assertIn(self.potter, switched)
        self.assertNotIn(self.ron, switched)
        self.assertNotIn(self.ron2, switched)

        self.assertIn(self.ron, duplicates)
        self.assertIn(self.ron2, duplicates)
        self.assertNotIn(self.harry, duplicates)
        self.assertNotIn(self.potter, duplicates)

    def test_not_finding_partially_reviewed_duplicates(self):
        """Ensure that if some records from the duplicated/switched
        names pair don't show up in the results, the other records won't
        either."""

        # modify duplication_reviewed_on to point to the
        # same date that last_updated_at will after save()
        # so that these records don't show up in results
        review_date = timezone.now()

        self.harry.duplication_reviewed_on = review_date
        self.harry.save()
        # self.potter.duplication_reviewed_on = review_date
        # self.potter.save()
        self.ron.duplication_reviewed_on = review_date
        self.ron.save()
        # self.ron2.duplication_reviewed_on = review_date
        # self.ron2.save()

        rv = self.client.get(self.url)
        switched = rv.context["switched_persons"]
        duplicates = rv.context["duplicate_persons"]

        self.assertNotIn(self.harry, switched)
        self.assertNotIn(self.potter, switched)
        self.assertNotIn(self.ron, switched)
        self.assertNotIn(self.ron2, switched)

        self.assertNotIn(self.ron, duplicates)
        self.assertNotIn(self.ron2, duplicates)
        self.assertNotIn(self.harry, duplicates)
        self.assertNotIn(self.potter, duplicates)

    def test_reviewing_persons(self):
        self.assertFalse(self.harry.duplication_reviewed_on)
        self.assertFalse(self.ron.duplication_reviewed_on)

        rv = self.client.post(
            self.review_url, {"person_id": [self.harry.pk, self.ron.pk]}
        )

        self.harry.refresh_from_db()
        self.ron.refresh_from_db()
        self.assertTrue(self.harry.duplication_reviewed_on)
        self.assertTrue(self.ron.duplication_reviewed_on)
