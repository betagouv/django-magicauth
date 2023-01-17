from django.contrib.auth import models as auth_models

from magicauth import settings as magicauth_settings

from . import utils


class DefaultAccountAdapter:
    def __init__(self, request=None):
        self.request = request

    def get_from_email(self):
        """
        This is a hook that can be overridden to programatically
        set the 'from' email address for sending emails
        """
        return magicauth_settings.FROM_EMAIL

    def email_unknown_callback(self, request, user_email, form):
        """
        Method to call when the email entered in the form is not found in the database.
        The default just raises an error whose message gets displayed on the login page.
        """
        utils.raise_error(email=user_email)


def get_adapter(request=None):
    return utils.import_attribute(magicauth_settings.ADAPTER)(request)
