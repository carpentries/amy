from django.urls import reverse

from workshops.tests.base import TestBase


class TestBadge(TestBase):
    """Tests for badge model and views, including some tests for awards."""

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_badge_display(self):
        """Ensure the badge is displayed correctly on its details page."""
        rv = self.client.get(reverse("badge_details", args=(self.swc_instructor.name,)))
        content = rv.content.decode("utf-8")
        assert self.swc_instructor.name in content
        assert self.swc_instructor.title in content
        assert self.swc_instructor.criteria in content
        self.assertEqual(rv.status_code, 200)

    def test_badge_display_awards(self):
        "Ensure awards are displayed correctly on their badge details page."
        rv = self.client.get(reverse("badge_details", args=(self.swc_instructor.name,)))
        content = rv.content.decode("utf-8")

        awards = self.swc_instructor.award_set.all()
        for award in awards:
            assert award.person.full_name in content, "Award for {} not found".format(
                award.person
            )

    def test_badge_award(self):
        """Ensure we can add awards from badge_award page."""
        swc_badge = self.app.get(
            reverse("badge_details", args=[self.swc_instructor.name]), user="admin"
        )
        award_add = swc_badge.click("Award new", index=0)
        form = award_add.forms[2]
        self.assertSelected(form["award-badge"], "Software Carpentry Instructor")
        form["award-person"].force_value(self.spiderman.id)
        assert self.swc_instructor.award_set.count() == 3
        form.submit()
        assert self.swc_instructor.award_set.count() == 4

    def test_remove_award(self):
        "Remove a badge from someone (ie. remove corresponding Award object)."
        person = self.hermione
        award = person.award_set.all()[0]
        badge = award.badge

        rv = self.client.post(
            "{}?next={}".format(
                reverse("award_delete", args=[award.pk]), reverse("admin-dashboard"),
            ),
            follow=True,
        )
        self.assertRedirects(rv, reverse("admin-dashboard"))

        assert award not in badge.award_set.all()  # award really removed
        assert badge not in person.badges.all()  # badge not avail. via Awards
