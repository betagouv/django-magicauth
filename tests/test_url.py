from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("", include("magicauth.urls")),
    path(
        "landing/", TemplateView.as_view(template_name="home.html"), name="test_home"
    ),
]
