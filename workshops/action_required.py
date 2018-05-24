from django.shortcuts import redirect
from django.urls import reverse

class PrivacyPolicy:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        url = reverse('action_required_privacy')

        allowed_urls = [
            reverse('logout'),
            url
        ]

        # redirect only users who didn't agree on the privacy policy
        # also don't redirect if the requested page is the page we want to
        # redirect to
        if (
                request.path not in allowed_urls and
                not request.user.is_anonymous and
                hasattr(request.user, 'data_privacy_agreement') and
                not request.user.data_privacy_agreement
            ):
                return redirect(url)
        else:
            return self.get_response(request)
