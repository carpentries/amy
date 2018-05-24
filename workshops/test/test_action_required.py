from django.urls import reverse

from .base import TestBase
from ..forms import ActionRequiredPrivacyForm
from ..models import Person


class TestActionRequiredPrivacy(TestBase):
    def setUp(self):
        super()._setUpAirports()
        super()._setUpBadges()
        self.neville = Person.objects.create(
            personal='Neville', family='Longbottom',
            email='neville@longbottom.com', gender='M', may_contact=True,
            publish_profile=False, airport=self.airport_0_0,
            username='longbottom_neville',
            data_privacy_agreement=False,
            is_active=True,
        )
        self.neville.save()

    def test_agreement_already_set(self):
        """Make sure the view redirect somewhere if person has already agreed
        to the privacy policy."""
        # force login Neville
        self.client.force_login(self.neville)

        url = reverse('action_required_privacy')

        # form renders
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

        # Neville decided to agree on the privacy policy for this test
        self.neville.data_privacy_agreement = True
        self.neville.save()

        # form redirects
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 302)

    def test_agreement_submit(self):
        "Make sure the form passes only when `data_agreement_policy` is set."
        # setup sample data
        data = {
            'data_privacy_agreement': False,
            'may_contact': False,
            'publish_profile': False,
        }

        # make sure it doesn't pass without the privacy policy consent
        form = ActionRequiredPrivacyForm(data, instance=self.neville)
        self.assertFalse(form.is_valid())

        # let's try with consent for privacy policy
        data.update({'data_privacy_agreement': True})
        form = ActionRequiredPrivacyForm(data, instance=self.neville)
        self.assertTrue(form.is_valid())


class TestActionRequiredPrivacyMiddleware(TestBase):
    def setUp(self):
        super()._setUpAirports()
        super()._setUpBadges()
        self.neville = Person.objects.create(
            personal='Neville', family='Longbottom',
            email='neville@longbottom.com', gender='M', may_contact=True,
            publish_profile=False, airport=self.airport_0_0,
            username='longbottom_neville',
            data_privacy_agreement=False,
            is_active=True,
        )
        self.neville.save()
        self.form_url = reverse('action_required_privacy')

    def test_anonymous_user(self):
        """Ensure anonymous user can reach anything."""
        urls = [
            reverse('login'),
            reverse('api:root'),
            reverse('swc_workshop_request'),
            reverse('dc_workshop_request'),
            reverse('dc_workshop_selforganized_request'),
            reverse('event_submit'),
            reverse('profileupdate_request'),
            reverse('training_request'),
            reverse('training_request_confirm'),
        ]
        # ensure we're not logged in
        self.client.logout()

        for url in urls:
            rv = self.client.get(url)
            # no redirects!
            self.assertEqual(rv.status_code, 200)
            # user indeed is anonymous
            self.assertEqual(rv.wsgi_request.user.is_anonymous, True)

    def test_logged_in_user(self):
        """Ensure logged-in user w/o privacy policy agreement is redirected
        to the form."""
        urls = [
            reverse('admin-dashboard'),
            reverse('trainee-dashboard'),
        ]

        form_url = reverse('action_required_privacy')

        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(self.neville.data_privacy_agreement, False)

        for url in urls:
            rv = self.client.get(url)
            # redirects to the form
            self.assertEqual(rv.status_code, 302)
            self.assertEqual(rv['Location'], form_url)

    def test_no_more_redirects_after_agreement(self):
        """Ensure user is no longer forcefully redirected to accept the
        privacy policy."""
        url = reverse('trainee-dashboard')
        form_url = reverse('action_required_privacy')

        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(self.neville.data_privacy_agreement, False)

        # we can't get to the url because we're redirected to the form
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 302)
        self.assertEqual(rv['Location'], form_url)

        # agree on the privacy policy
        self.neville.data_privacy_agreement = True
        self.neville.save()

        # now the dashboard is easily reachable
        rv = self.client.get(url)
        self.assertEqual(rv.status_code, 200)

    def test_allowed_urls(self):
        form_url = reverse('action_required_privacy')
        urls = [
            reverse('logout'),
        ]
        # ensure we're logged in
        self.client.force_login(self.neville)
        self.assertEqual(self.neville.data_privacy_agreement, False)
        for url in urls:
            rv = self.client.get(url)
            # doesn't redirect to the form
            self.assertIn(rv.status_code, [200, 302])
            if 'Location' in rv:
                self.assertNotEqual(rv['Location'], form_url)
