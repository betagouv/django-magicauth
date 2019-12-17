from django.urls import path

from . import views as magicauth_views
from . import settings as magicauth_settings

urlpatterns = [
    path(
        magicauth_settings.LOGIN_URL,
        magicauth_views.LoginView.as_view(),
        name="magicauth-login",
    ),
    path(
        magicauth_settings.EMAIL_SENT_URL,
        magicauth_views.EmailSentView.as_view(),
        name="magicauth-email-sent",
    ),
    path(
        magicauth_settings.WAIT_URL,
        magicauth_views.WaitView.as_view(),
        name="magicauth-wait",
    ),
    path(
        magicauth_settings.VALIDATE_TOKEN_URL,
        magicauth_views.ValidateTokenView.as_view(),
        name="magicauth-validate-token",
    ),
]
