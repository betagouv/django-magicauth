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


def get_adapter(request=None):
    return utils.import_attribute(magicauth_settings.ADAPTER)(request)
