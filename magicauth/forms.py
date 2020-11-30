from django import forms
from django.contrib.auth import get_user_model
from django.utils.module_loading import import_string
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from django_otp import user_has_device, devices_for_user

from magicauth import settings as magicauth_settings
from magicauth.models import MagicToken

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


class OTPForm(forms.Form):
    OTP_NUM_DIGITS = magicauth_settings.OTP_NUM_DIGITS
    otp_token = forms.CharField(
        max_length=OTP_NUM_DIGITS,
        min_length=OTP_NUM_DIGITS,
        validators=[RegexValidator(r"^\d{6}$")],
        label=f"Entrez le code à {OTP_NUM_DIGITS} chiffres généré par votre téléphone ou votre carte OTP",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    def __init__(self, user, *args, **kwargs):
        super(OTPForm, self).__init__(*args, **kwargs)
        self.user = user

    def clean_otp_token(self):
        otp_token = self.cleaned_data["otp_token"]
        user = self.user
        if not user_has_device(user):
            raise ValidationError("Le système n'a pas trouvé d'appareil (carte OTP ou générateur sur téléphone) pour votre compte. Contactez le support pour en ajouter un.")

        for device in devices_for_user(user):
            if not device.verify_is_allowed():
                raise ValidationError("Vous devez patienter avant de recommencer")
            if not device.verify_token(otp_token):
                raise ValidationError("Ce code n'est pas valide.")

        return otp_token

