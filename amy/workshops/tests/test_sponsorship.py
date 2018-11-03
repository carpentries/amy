from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import IntegrityError
from django.urls import reverse

from workshops.tests.base import TestBase
from workshops.models import Event, Organization, Sponsorship


class TestSponsorshipModel(TestBase):

    def setUp(self):
        super().setUp()
        self.event = Event.objects.create(
            slug='2016-07-05-test-event',
            host=self.org_alpha,
        )

    def test_positive_amount_field(self):
        '''Check that we cannot add negative amount of sponsorship'''
        with self.assertRaises(ValidationError):
            Sponsorship.objects.create(
                organization=self.org_beta,
                event=self.event,
                amount=-500,
            ).full_clean()

    def test_sponsorship_without_amount(self):
        '''Check that we can have blank amount field'''
        Sponsorship.objects.create(
            organization=self.org_beta,
            event=self.event,
        ).full_clean()


    def test_sponsorship_can_be_deleted_and_related_objects_are_intact(self):
        '''Check that the event and organization aren't deleted'''
        sponsorship = Sponsorship.objects.create(
            organization=self.org_beta,
            event=self.event,
            amount=-500,
        )
        sponsorship.delete()
        with self.assertRaises(ObjectDoesNotExist):
            sponsorship.refresh_from_db()
        # Raise ObjectDoesNotExist if deleted
        self.event.refresh_from_db()
        self.org_beta.refresh_from_db()

    def test_unique_together_constraint(self):
        '''Check that no two sponsorships with same values can exist'''
        sponsorship = Sponsorship.objects.create(
            organization=self.org_beta,
            event=self.event,
            amount=500,
        )
        with self.assertRaises(IntegrityError):
            sponsorship = Sponsorship.objects.create(
                organization=self.org_beta,
                event=self.event,
                amount=500,
            )


class TestSponsorshipViews(TestBase):

    def setUp(self):
        super().setUp()
        self.event = Event.objects.create(
            slug='2016-07-05-test-event',
            host=self.org_alpha,
        )
        self.sponsorship = Sponsorship.objects.create(
            organization=self.org_alpha,
            event=self.event,
            amount=1500,
        )
        self._setUpUsersAndLogin()

    def test_sponsor_visible_on_event_detail_page(self):
        '''Check that added sponsor is visible on the event detail page'''
        rv = self.client.get(
            reverse('event_details', kwargs={'slug': self.event.slug})
        )
        self.assertEqual(rv.status_code, 200)
        self.assertIn(self.sponsorship, rv.context['event'].sponsorship_set.all())

    def test_sponsor_visible_on_event_edit_page(self):
        rv = self.client.get(
            reverse('event_edit', kwargs={'slug': self.event.slug})
        )
        self.assertEqual(rv.status_code, 200)
        self.assertIn(self.sponsorship, rv.context['object'].sponsorship_set.all())

    def test_add_sponsor_minimal(self):
        '''Check that we can add a sponsor w/ minimal parameters'''
        payload = {
            'organization': self.org_beta.pk,
            'event': self.event.pk,
        }
        response = self.client.post(
            reverse('sponsorship_add'), payload, follow=True
        )
        self.assertRedirects(
            response,
            '{}#sponsors'.format(
                reverse('event_edit', kwargs={'slug': self.event.slug}),
            )
        )
        self.assertTrue(response.context['object'].sponsorship_set.all())
        self.assertEqual(response.context['object'].sponsors.count(), 2)

    def test_add_sponsor_with_amount(self):
        '''Check that we can add a sponsor with amount'''
        payload = {
            'organization': self.org_beta.pk,
            'event': self.event.pk,
            'amount': 1500,
        }
        response = self.client.post(
            reverse('sponsorship_add'), payload, follow=True
        )
        self.assertRedirects(
            response,
            '{}#sponsors'.format(
                reverse('event_edit', kwargs={'slug': self.event.slug}),
            )
        )
        self.assertTrue(response.context['object'].sponsorship_set.all())
        self.assertEqual(response.context['object'].sponsors.count(), 2)
        self.assertIn(
            1500,
            response.context['object'].sponsorship_set.values_list('amount', flat=True)
        )

    def test_add_sponsor_with_contact(self):
        '''Check that we can add a sponsor with a contact person'''
        payload = {
            'organization': self.org_beta.pk,
            'event': self.event.pk,
            'contact': self.harry.pk,
            'amount': 1500,
        }
        response = self.client.post(
            reverse('sponsorship_add'), payload, follow=True
        )
        self.assertRedirects(
            response,
            '{}#sponsors'.format(
                reverse('event_edit', kwargs={'slug': self.event.slug}),
            )
        )
        self.assertTrue(response.context['object'].sponsorship_set.all())
        self.assertEqual(response.context['object'].sponsors.count(), 2)
        self.assertIn(
            self.harry.pk,
            response.context['object'].sponsorship_set.values_list('contact', flat=True)
        )

    def test_add_duplicate_sponsorship_instance(self):
        '''Check that we cannot successfully submit duplicates'''
        payload = {
            'organization': self.sponsorship.organization.pk,
            'event': self.sponsorship.event.pk,
            'amount': self.sponsorship.amount,
        }
        response = self.client.post(
            reverse('sponsorship_add'), payload, follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response,
            form='form',
            field=None,
            errors='Sponsorship with this Organization, Event and Sponsorship amount already exists.',
        )

    def test_delete_sponsor(self):
        '''Check that we can delete a sponsor from `sponsor_delete` view'''
        response = self.client.post(
            reverse('sponsorship_delete', kwargs={'pk': self.sponsorship.pk}),
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('event_edit', kwargs={'slug': self.event.slug}) + '#sponsors',
        )
        self.assertFalse(response.context['object'].sponsorship_set.all())
        self.assertEqual(response.context['object'].sponsors.count(), 0)
        with self.assertRaises(ObjectDoesNotExist):
            self.sponsorship.refresh_from_db()
