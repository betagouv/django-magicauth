from datetime import timedelta

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import timezone
from django.utils.translation import gettext as _

from magicauth.models import MagicToken
from magicauth import settings as magicauth_settings


class OTPForm(forms.Form):
    OTP_NUM_DIGITS = magicauth_settings.OTP_NUM_DIGITS
    otp_token = forms.CharField(
        max_length=OTP_NUM_DIGITS,
        min_length=OTP_NUM_DIGITS,
        validators=[RegexValidator(r"^\d{6}$")],
        label=_(
            "Entrez le code à %(OTP_NUM_DIGITS)s chiffres généré par votre téléphone ou votre carte OTP"
        )
        % {"OTP_NUM_DIGITS": OTP_NUM_DIGITS},
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )

    def __init__(self, user, *args, **kwargs):
        super(OTPForm, self).__init__(*args, **kwargs)
        self.user = user

    def clean_otp_token(self):
        from django_otp import user_has_device, devices_for_user

        otp_token = self.cleaned_data["otp_token"]
        user = self.user
        if not user_has_device(user):
            raise ValidationError(
                _(
                    "Le système n'a pas trouvé d'appareil (carte OTP ou générateur sur téléphone) pour votre compte. "
                    "Contactez le support pour en ajouter un."
                )
            )

        for device in devices_for_user(user):
            if device.verify_is_allowed() and device.verify_token(otp_token):
                return otp_token

        raise ValidationError(_("Ce code n'est pas valide."))


class TokenValidationForm(forms.Form):
    token = forms.CharField()

    def clean_token(self):
        token = self.cleaned_data.get("token")
        try:
            token = MagicToken.objects.get(key=token)
            if token.created < timezone.now() - timedelta(
                seconds=magicauth_settings.TOKEN_DURATION_SECONDS
            ):
                # Do not raise here as we still want to cache the token in cleaned_data
                # for further manipulations
                self.add_error("token", ValidationError("", code="token_expired"))
            return token
        except MagicToken.DoesNotExist:
            raise ValidationError("", code="token_does_not_exist")
        except MagicToken.MultipleObjectsReturned:
            raise ValidationError("", code="multiple_token_returned")
