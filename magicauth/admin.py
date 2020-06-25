from django.contrib import admin

from .models import MagicToken


@admin.register(MagicToken)
class MagicTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created", "key")
    raw_id_fields = ("user",)
