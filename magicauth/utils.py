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
