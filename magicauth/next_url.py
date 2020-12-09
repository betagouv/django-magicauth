import urllib.parse
import logging

from django.http import Http404
from django.urls import reverse
try:
    from django.utils.http import url_has_allowed_host_and_scheme
except ImportError:
    # For Django < v3, use old deprecated function
    from django.utils.http import is_safe_url as url_has_allowed_host_and_scheme

from magicauth import settings as magicauth_settings


logger = logging.getLogger()


class NextUrlMixin(object):
    """
    Helper for managing the 'next url' parameter.
    """

    def get_next_url(self, request):
        """
        Get the next url from the querystring parameters (?next=/my/next/page).
        If the next parameter is not there, returns the default redirect url
        """
        next_url = request.GET.get("next")
        if not next_url:
            next_url = reverse(magicauth_settings.LOGGED_IN_REDIRECT_URL_NAME)
        if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=True):
            # We are not logging the unsafe URL to prevent code injections in logs
            logger.warning("[MagicAuth] an unsafe URL was used through a login link")
            raise Http404
        return next_url

    def get_next_url_encoded(self, request):
        """
        Use this when the URL needs to be encoded, for instance when including the URL to string
        before a redirect.
        """
        url = self.get_next_url(self.request)
        return urllib.parse.quote(url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        next_url = self.get_next_url(self.request)
        context["next_url"] = next_url
        return context
