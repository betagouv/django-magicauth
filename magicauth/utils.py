from django import forms
from django.urls import reverse_lazy

import binascii
import os
import re

from . import settings as magicauth_settings


def generate_token():
    return binascii.hexlify(os.urandom(20)).decode()


def raise_error(email=None):
    """
    Just raise an error - this can be used as a call back function
    when no user was found in DB during the login process.
    """
    raise forms.ValidationError(magicauth_settings.EMAIL_UNKNOWN_MESSAGE)


def get_next_view(request):
    """
    Get the next view from the url query parameters (?next=url)
    """
    full_path = request.get_full_path()
    rule_for_redirect = re.compile("(.*next=)(.*)")
    next_view = rule_for_redirect.match(full_path)
    redirect_default = reverse_lazy(magicauth_settings.LOGGED_IN_REDIRECT_URL_NAME)
    return next_view.group(2) if next_view else redirect_default
