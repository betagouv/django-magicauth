import re
import logging
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.http import HttpResponseNotFound
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.http import is_safe_url
from django.views.generic import View, FormView, TemplateView

from magicauth.forms import EmailForm
from magicauth.models import MagicToken
from magicauth import settings as magicauth_settings

logger = logging.getLogger()

class LoginView(FormView):
    """
    The login page. The user enters their email in the form to get a link by email.
    """

    form_class = EmailForm
    success_url = reverse_lazy("magicauth-email-sent")
    template_name = magicauth_settings.LOGIN_VIEW_TEMPLATE

    def get(self, request, *args, **kwargs):
        next_view = self.request.GET.get(
            "next", f"/{magicauth_settings.LOGGED_IN_REDIRECT_URL_NAME}/"
        )
        if request.user.is_authenticated:
            return redirect(next_view)

        return super(LoginView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        context[
            "LOGGED_IN_REDIRECT_URL_NAME"
        ] = magicauth_settings.LOGGED_IN_REDIRECT_URL_NAME
        context["LOGOUT_URL_NAME"] = magicauth_settings.LOGOUT_URL_NAME
        return context

    def form_valid(self, form, *args, **kwargs):
        next_view = self.request.GET.get(
            "next",
            f"/{magicauth_settings.LOGGED_IN_REDIRECT_URL_NAME}/"
        )
        current_site = self.request.site
        form.send_email(current_site, next_view)
        return super().form_valid(form)


class EmailSentView(TemplateView):
    """
    View shown to confirm the email has been sent.
    """

    template_name = magicauth_settings.EMAIL_SENT_VIEW_TEMPLATE


class ValidateTokenView(View):
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
        full_path = request.get_full_path()

        rule_for_redirect = re.compile("(.*next=)(.*)")
        next_view = rule_for_redirect.match(full_path)
        redirect_default = reverse_lazy(magicauth_settings.LOGGED_IN_REDIRECT_URL_NAME)
        url = next_view.group(2) if next_view else redirect_default

        # the following `is_safe_url` will be deprecated in django 4 and replaced by url_has_allowed_host_and_scheme
        if not is_safe_url(url, allowed_hosts={request.get_host()}, require_https=True):
            # We are not logging the unsafe URL to prevent code injections in logs
            logger.warning("[MagicAuth] an unsafe URL was used through a login link")
            return HttpResponseNotFound()

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
