from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import RegexValidator
from django.template import loader
from django.utils.module_loading import import_string
from django_otp import match_token
from magicauth import settings as magicauth_settings
from magicauth.models import MagicToken
import math


email_unknown_callback = import_string(magicauth_settings.EMAIL_UNKNOWN_CALLBACK)


class EmailForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        user_email = self.cleaned_data["email"]
        user_email = user_email.lower()

        email_field = magicauth_settings.EMAIL_FIELD
        field_lookup = {f"{email_field}__iexact": user_email}

        if not get_user_model().objects.filter(**field_lookup).exists():
            email_unknown_callback(user_email)
        return user_email

    def create_token(self, user):
        token = MagicToken.objects.create(user=user)
        return token

    def send_email(self, current_site, next_url):
        user_email = self.cleaned_data["email"]
        email_field = magicauth_settings.EMAIL_FIELD
        field_lookup = {f"{email_field}__iexact": user_email}
        user = get_user_model().objects.get(**field_lookup)
        token = self.create_token(user)
        email_subject = magicauth_settings.EMAIL_SUBJECT
        html_template = magicauth_settings.EMAIL_HTML_TEMPLATE
        text_template = magicauth_settings.EMAIL_TEXT_TEMPLATE
        from_email = magicauth_settings.FROM_EMAIL
        context = {
            "token": token,
            "user": user,
            "site": current_site,
            "next_url": next_url,
            "TOKEN_DURATION_MINUTES": math.floor(magicauth_settings.TOKEN_DURATION_SECONDS / 60),
            "TOKEN_DURATION_SECONDS": magicauth_settings.TOKEN_DURATION_SECONDS,
        }
        text_message = loader.render_to_string(text_template, context)
        html_message = loader.render_to_string(html_template, context)
        send_mail(
            subject=email_subject,
            message=text_message,
            from_email=from_email,
            html_message=html_message,
            recipient_list=[user_email],
            fail_silently=False,
        )


class OTPForm(forms.Form):
    otp_token = forms.CharField(
        max_length=6,
        min_length=6,
        validators=[RegexValidator(r"^\d{6}$")],
        label="Entrez le code à 6 chiffres généré par votre téléphone",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    def __init__(self, user, *args, **kwargs):
        super(OTPForm, self).__init__(*args, **kwargs)
        self.user = user

    def clean_otp_token(self):
        otp_token = self.cleaned_data["otp_token"]
        user = self.user
        from django_otp import user_has_device, devices_for_user
        if not user_has_device(user):
            raise ValidationError("Vous n'avez pas d'appareil enregistré")

        for device in devices_for_user(user):
            if not device.verify_is_allowed():
                raise ValidationError("Vous devez patienter avant de recommencer")
            if device.verify_token(otp_token):
                return otp_token
        raise ValidationError("Ce code n'est pas valide.")
