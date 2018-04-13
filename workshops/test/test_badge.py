import hashlib
import unittest

from django.core.urlresolvers import reverse

from .base import TestBase
from ..models import Badge, Award, Person, Event


class TestBadge(TestBase):
    """Tests for badge model and views, including some tests for awards."""

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_badge_display(self):
        """Ensure the badge is displayed correctly on its details page."""
        rv = self.client.get(reverse('badge_details',
                                     args=(self.swc_instructor.name, )))
        content = rv.content.decode('utf-8')
        assert self.swc_instructor.name in content
        assert self.swc_instructor.title in content
        assert self.swc_instructor.criteria in content
        self._check_status_code_and_parse(rv, 200)

    def test_badge_display_awards(self):
        "Ensure awards are displayed correctly on their badge details page."
        rv = self.client.get(reverse('badge_details',
                                     args=(self.swc_instructor.name, )))
        content = rv.content.decode('utf-8')

        awards = self.swc_instructor.award_set.all()
        for award in awards:
            assert award.person.get_full_name() in content, \
                "Award for {} not found".format(award.person)

    def test_badge_award(self):
        """Ensure we can add awards from badge_award page."""
        swc_badge = self.app.get(
            reverse('badge_details', args=[self.swc_instructor.name, ]),
            user='admin'
        )
        award_add = swc_badge.click('Award new', index=0)
        form = award_add.forms[2]
        self.assertSelected(form['badge'], 'Software Carpentry Instructor')
        form['person_1'] = self.spiderman.id
        assert self.swc_instructor.award_set.count() == 3
        form.submit()
        assert self.swc_instructor.award_set.count() == 4

    def test_remove_award(self):
        "Remove a badge from someone (ie. remove corresponding Award object)."
        person = self.hermione
        award = person.award_set.all()[0]
        badge = award.badge

        rv = self.client.post(
            '{}?next={}'.format(
                reverse('award_delete', args=[award.pk]),
                reverse('admin-dashboard'),
            ),
            follow=True
        )
        self.assertRedirects(rv, reverse('admin-dashboard'))

        assert award not in badge.award_set.all()  # award really removed
        assert badge not in person.badges.all()  # badge not avail. via Awards


class TestCertification(TestBase):
    SWC_INSTRUCTOR_HARRY = '9fe2bfd6b2c2a80aa1d0f6420883f72e'
    DC_INSTRUCTOR_HERMIONE = '757a3285a7ececb19c5c2a266cd11b67'
    MAINTAINER_SPIDERMAN = '5db0dbb577dfd22ff1730190c6ffd791'
    ORGANIZER_IRONMAN = ''

    def setUp(self):
        super().setUp()
        self._setUpUsersAndLogin()

    def test_swc_instructor_certification(self):
        swc_award = self.harry.award_set.first()
        certificate = self.client.get(
            reverse('award_certificate', args=[swc_award.pk]))
        self.assertEqual(
            hashlib.md5(certificate.content).hexdigest(),
            self.SWC_INSTRUCTOR_HARRY
        )

    def test_dc_instructor_certification(self):
        dc_award = self.hermione.award_set.last()
        certificate = self.client.get(
            reverse('award_certificate', args=[dc_award.pk]))
        self.assertEqual(
            hashlib.md5(certificate.content).hexdigest(),
            self.DC_INSTRUCTOR_HERMIONE
        )

    def test_maintainer_certification(self):
        maintainer_award = self.spiderman.award_set.first()
        certificate = self.client.get(
            reverse('award_certificate', args=[maintainer_award.pk]))
        self.assertEqual(
            hashlib.md5(certificate.content).hexdigest(),
            self.MAINTAINER_SPIDERMAN,
        )

    @unittest.expectedFailure
    def test_organizer_certification(self):
        organizer_award = self.ironman.award_set.first()
        certificate = self.client.get(
            reverse('award_certificate', args=[organizer_award.pk]))
        self.assertEqual(
            hashlib.md5(certificate.content).hexdigest(),
            self.ORGANIZER_IRONMAN,
        )
