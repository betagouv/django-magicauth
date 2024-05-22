import logging
import warnings

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.forms.utils import ErrorList
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_GET
from django.views.generic import FormView, TemplateView

from magicauth import settings as magicauth_settings
from magicauth.forms import EmailForm
from magicauth.models import MagicToken
from magicauth.next_url import NextUrlMixin
from magicauth.send_token import SendTokenMixin

try:
    from magicauth.otp_forms import OTPForm, TokenValidationForm
except ImportError:
    pass  # OTP form class is optional


logger = logging.getLogger()


class LoginView(NextUrlMixin, SendTokenMixin, FormView):
    """
    Step 1 of login process : GET the LoginView.
    Step 2 of login process : POST your email to the LoginView.
    """

    form_class = EmailForm
    otp_form_class = OTPForm
    success_url = reverse_lazy("magicauth-email-sent")
    template_name = magicauth_settings.LOGIN_VIEW_TEMPLATE
    use_deprecated_login_for_errors = True

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            next_url = self.get_next_url(self.request)
            return redirect(next_url)
        return super(LoginView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        if magicauth_settings.ENABLE_2FA and "OTP_form" not in kwargs:
            kwargs["OTP_form"] = self.get_otp_form()
        return super(LoginView, self).get_context_data(
            **kwargs,
            LOGGED_IN_REDIRECT_URL_NAME=magicauth_settings.LOGGED_IN_REDIRECT_URL_NAME,
            LOGOUT_URL_NAME=magicauth_settings.LOGOUT_URL_NAME,
            OTP_enabled=magicauth_settings.ENABLE_2FA,
        )

    def get_success_url(self, **kwargs):
        url = reverse_lazy("magicauth-email-sent")
        # Use encoded next URL before including it in a string
        next_url_quoted = self.get_next_url_encoded(self.request)
        return f"{url}?next={next_url_quoted}"

    def form_valid(self, form, *args, **kwargs):
        user_email = form.cleaned_data["email"]
        context = {"next_url": self.get_next_url(self.request)}

        user = self.get_user(user_email)
        otp_form = self.get_otp_form(user)

        if magicauth_settings.ENABLE_2FA and not otp_form.is_valid():
            return self.otp_form_invalid(form, otp_form)

        self.send_token(user_email=user_email, extra_context=context)
        return super().form_valid(form)

    def get_user(self, user_email):
        email_field = "%s__iexact" % magicauth_settings.EMAIL_FIELD
        return get_user_model().objects.get(**{email_field: user_email})

    def otp_form_invalid(self, form, otp_form):
        if self.use_deprecated_login_for_errors:
            # This should be done on the client side if needed
            msg = (
                "Adding otp_form_class.otp_token to form_class.email will be "
                "deprecated in the future. This can be deactivated right now by "
                "setting LoginView.use_deprecated_login_for_errors to False."
            )
            warnings.warn(msg, DeprecationWarning)
            logging.getLogger(__file__).warning(f"DEPRECATION: {msg}")

            for error in otp_form.errors["otp_token"]:
                form.add_error("email", error)

        return self.render_to_response(
            self.get_context_data(form=form, OTP_form=otp_form)
        )

    def get_otp_form_class(self):
        return self.otp_form_class

    def get_otp_form(self, user=None):
        return self.get_otp_form_class()(**self.get_otp_form_kwargs(user))

    def get_otp_form_kwargs(self, user=None):
        kwargs = {
            "user": user or self.request.user,
            "initial": self.get_initial(),
            "prefix": self.get_prefix(),
        }

        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs


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
        validate_token_url = reverse(
            "magicauth-validate-token", kwargs={"key": token_key}
        )
        next_url_quoted = self.get_next_url_encoded(self.request)
        context["next_step_url"] = f"{validate_token_url}?next={next_url_quoted}"
        context["WAIT_SECONDS"] = magicauth_settings.WAIT_SECONDS
        return context


@method_decorator(require_GET, name="dispatch")
class ValidateTokenView(NextUrlMixin, FormView):
    form_class = TokenValidationForm
    """
    Step 5 of login process : you visit the ValidateTokenView that validates the token, logs you in,
    and redirects you to the url in the "next" param (or the default view if no next).

    Either you clicked a link to this page in your email, or you got redirected from step 4
    (WaitView).

    If the token is invalid, you are not logged in, and you are redirected to LoginView (step 1) to
    start over.
    """

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "data": {"token": self.kwargs.get("key")}}

    def get(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_invalid(self, form):
        token = form.cleaned_data.get("token")
        error_codes = [err.code for err in form.errors.get("token", ErrorList()).data]
        if "token_expired" in error_codes:
            token.delete()

        return self.token_invalid()

    def token_invalid(self):
        messages.warning(
            self.request,
            "Ce lien de connexion ne fonctionne plus. "
            "Pour en recevoir un nouveau, nous vous invitons à renseigner "
            "votre email ci-dessous puis à cliquer sur valider.",
        )
        return redirect(reverse("magicauth-login"))

    def form_valid(self, form):
        # Early compute success URL for validation before login
        success_url = self.get_success_url()

        token = form.cleaned_data["token"]
        try:
            login(
                self.request,
                token.user,
                backend=magicauth_settings.DEFAULT_AUTHENTICATION_BACKEND,
            )
        except ValueError as e:
            raise ValueError(
                "You have multiple authentication backends configured and therefore "
                "must define the MAGICAUTH_DEFAULT_AUTHENTICATION_BACKEND setting. "
                "MAGICAUTH_DEFAULT_AUTHENTICATION_BACKEND should be a "
                "dotted import path string."
            ) from e
        # Remove them all for this user
        MagicToken.objects.filter(user=token.user).delete()
        return redirect(success_url)

    def get_success_url(self):
        return self.get_next_url(self.request)
