from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("", include("magicauth.urls")),
    path(
        "test_home/", TemplateView.as_view(template_name="home.html"), name="test_home"
    ),
]
