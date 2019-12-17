import re
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import View, FormView, TemplateView
from magicauth.forms import EmailForm
from magicauth.models import MagicToken
from magicauth import settings as magicauth_settings


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


class WaitView(TemplateView):
    """
    The view shows few seconds of wait, and then the user is redirected to login.
    This is for solving an issue where antispam mail clients visit links in email to check them, and thus invalidate
    our token.
    """
    template_name = magicauth_settings.WAIT_VIEW_TEMPLATE

    # todo : reuse method
    @staticmethod
    def get_next_view(request):
        full_path = request.get_full_path()
        rule_for_redirect = re.compile("(.*next=)(.*)")
        next_view = rule_for_redirect.match(full_path)
        redirect_default = reverse_lazy(magicauth_settings.LOGGED_IN_REDIRECT_URL_NAME)
        return next_view.group(2) if next_view else redirect_default

    def get_context_data(self, **kwargs):
        context = super(WaitView, self).get_context_data(**kwargs)

        next_view = self.get_next_view(self.request)
        token_key = kwargs.get("key")
        url = f"{reverse_lazy('magicauth-validate-token', kwargs={ 'key': token_key })}?next={ next_view }"
        context["url"] = url

        # todo put that value in settings somewhere
        context["WAIT_SECONDS"] = magicauth_settings.WAIT_SECONDS

        return context


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

    @staticmethod
    def get_next_view(request):
        full_path = request.get_full_path()
        rule_for_redirect = re.compile("(.*next=)(.*)")
        next_view = rule_for_redirect.match(full_path)
        redirect_default = reverse_lazy(magicauth_settings.LOGGED_IN_REDIRECT_URL_NAME)
        return next_view.group(2) if next_view else redirect_default

    def get(self, request, *args, **kwargs):
        url = self.get_next_view(request)

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
