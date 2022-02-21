from django import forms
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

from django_otp import user_has_device, devices_for_user

from magicauth import settings as magicauth_settings


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
            if device.verify_is_allowed() and device.verify_token(otp_token):
                return otp_token

        raise ValidationError("Ce code n'est pas valide.")
