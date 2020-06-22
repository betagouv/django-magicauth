from datetime import timedelta
import logging
import urllib.parse

from django.contrib import messages
from django.contrib.auth import login
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.http import is_safe_url
from django.views.generic import View, FormView, TemplateView

from magicauth import settings as magicauth_settings
from magicauth.forms import EmailForm
from magicauth.models import MagicToken

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
        # the following `is_safe_url` will be deprecated in django 4 and replaced by
        # url_has_allowed_host_and_scheme
        if not is_safe_url(next_url, allowed_hosts={request.get_host()}, require_https=True):
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


class LoginView(NextUrlMixin, FormView):
    """
    The login page. The user enters their email in the form to get a link by email.
    """

    form_class = EmailForm
    success_url = reverse_lazy("magicauth-email-sent")
    template_name = magicauth_settings.LOGIN_VIEW_TEMPLATE

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            next_url = self.get_next_url(self.request)
            return redirect(next_url)
        return super(LoginView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        context[
            "LOGGED_IN_REDIRECT_URL_NAME"
        ] = magicauth_settings.LOGGED_IN_REDIRECT_URL_NAME
        context["LOGOUT_URL_NAME"] = magicauth_settings.LOGOUT_URL_NAME
        return context

    def get_success_url(self, **kwargs):
        url = reverse_lazy("magicauth-email-sent")
        # Use encoded next URL before including it in a string
        next_url_quoted = self.get_next_url_encoded(self.request)
        return f"{url}?next={next_url_quoted}"

    def form_valid(self, form, *args, **kwargs):
        next_url = self.get_next_url(self.request)
        current_site = self.request.site
        form.send_email(current_site, next_url)
        return super().form_valid(form)


class EmailSentView(NextUrlMixin, TemplateView):
    """
    View shown to confirm the email has been sent.
    """
    template_name = magicauth_settings.EMAIL_SENT_VIEW_TEMPLATE


class WaitView(NextUrlMixin, TemplateView):
    """
    Wait few seconds before redirecting to login.
    This is for solving an issue with a security feature in some email clients where
    the magic link is verified and and thus the token gets invalidated.
    """
    template_name = magicauth_settings.WAIT_VIEW_TEMPLATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token_key = kwargs.get("key")
        validate_token_url = reverse('magicauth-validate-token', kwargs={'key': token_key})
        context["validate_token_url"] = validate_token_url
        context["WAIT_SECONDS"] = magicauth_settings.WAIT_SECONDS
        return context


class ValidateTokenView(NextUrlMixin, View):
    """
    The link sent by email goes to this view.
    It validates the token passed in querystring,
    and either logs in or shows a form to make a new token.
    """

    @staticmethod
    def get_valid_token(key):
        duration = magicauth_settings.TOKEN_DURATION_SECONDS
        try:
            token = MagicToken.objects.get(key=key)
        except MagicToken.DoesNotExist:
            return None
        except MagicToken.MultipleObjectsReturned:
            return None

        if token.created < timezone.now() - timedelta(seconds=duration):
            token.delete()
            return None
        return token

    def get(self, request, *args, **kwargs):
        url = self.get_next_url(request)
        if request.user.is_authenticated:
            return redirect(url)
        token_key = kwargs.get("key")
        token = self.get_valid_token(token_key)
        if not token:
            messages.warning(
                self.request,
                "Ce lien de connexion ne fonctionne plus. "
                "Pour en recevoir un nouveau, nous vous invitons à renseigner "
                "votre email ci-dessous puis à cliquer sur valider.",
            )
            return redirect("magicauth-login")
        login(self.request, token.user)
        MagicToken.objects.filter(
            user=token.user
        ).delete()  # Remove them all for this user
        return redirect(url)
