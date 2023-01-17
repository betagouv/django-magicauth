from django import forms
from django.contrib.auth import get_user_model
from django.utils.module_loading import import_string

from magicauth import settings as magicauth_settings


class EmailForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        user_email = self.cleaned_data["email"]
        user_email = user_email.lower()

        return user_email
