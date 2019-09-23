from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

from .utils import generate_token


class MagicToken(models.Model):
    key = models.CharField(
        verbose_name=_("Key"), primary_key=True, default=generate_token, max_length=255
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="magic_token", on_delete=models.CASCADE
    )
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Magic Token"
        verbose_name_plural = _("Magic Tokens")
        ordering = ("-created",)

    def __str__(self):
        return self.key
