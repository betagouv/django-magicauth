from datetime import timedelta
import logging

from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import View, FormView, TemplateView

from magicauth import settings as magicauth_settings
from magicauth.forms import EmailForm
from magicauth.models import MagicToken
from magicauth.next_url import NextUrlMixin
from magicauth.send_token import SendTokenMixin


logger = logging.getLogger()


class LoginView(NextUrlMixin, SendTokenMixin, FormView):
    """
    Step 1 of login process : GET the LoginView.
    Step 2 of login process : POST your email to the LoginView.
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
        user_email = form.cleaned_data["email"]
        context = {"next_url": self.get_next_url(self.request)}
        self.send_token(user_email=user_email, extra_context=context)
        return super().form_valid(form)


class EmailSentView(NextUrlMixin, TemplateView):
    """
    Step 3 of login process : you get a confirmation page that the email was sent.
    """
    template_name = magicauth_settings.EMAIL_SENT_VIEW_TEMPLATE


class WaitView(NextUrlMixin, TemplateView):
    """
    Step 4 of login process (optional): you visit the link that you got by email that sends you to
    the WaitView.
    If the WaitView is not used, then the link will send you directly to step 5, token validation.

    Th WaitView will wait few seconds, redirect you to the token validation.
    This is for solving an issue with a security feature in some email clients where
    the magic link is verified and and thus the token gets invalidated by the email client.
    """
    template_name = magicauth_settings.WAIT_VIEW_TEMPLATE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token_key = kwargs.get("key")
        validate_token_url = reverse('magicauth-validate-token', kwargs={'key': token_key})
        next_url_quoted = self.get_next_url_encoded(self.request)
        context["next_step_url"] = f"{validate_token_url}?next={next_url_quoted}"
        context["WAIT_SECONDS"] = magicauth_settings.WAIT_SECONDS
        return context


class ValidateTokenView(NextUrlMixin, View):
    """
    Step 5 of login process : you visit the ValidateTokenView that validates the token, logs you in,
    and redirects you to the url in the "next" param (or the default view if no next).

    Either you clicked a link to this page in your email, or you got redirected from step 4
    (WaitView).

    If the token is invalid, you are not logged in, and you are redirected to LoginView (step 1) to
    start over.
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
