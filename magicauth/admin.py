from django.contrib import admin

from .models import MagicToken


@admin.register(MagicToken)
class MagicTokenAdmin(admin.ModelAdmin):
    list_display = ("key", "user", "created")
    raw_id_fields = ("user",)
