from pytest import mark

from django.shortcuts import reverse
from magicauth import settings
from tests import factories

'''
Step 1 of login process : see doc in magicauth/views.py for step details
'''

pytestmark = mark.django_db


def test_unauthenticated_user_accesses_login_page(client):
    url = reverse("magicauth-login")
    response = client.get(url)
    assert response.status_code == 200


def test_authenticated_user_is_redirected_to_default_redirect_page(client):
    user = factories.UserFactory()
    client.force_login(user)
    url = reverse("magicauth-login")
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == "/landing/"


def test_authenticated_user_is_redirected_to_next_url(client):
    user = factories.UserFactory()
    client.force_login(user)
    url = reverse("magicauth-login")
    response = client.get(url, {"next": "/test_dashboard/"})
    assert response.status_code == 302
    assert response.url == "/test_dashboard/"


def test_login_page_raises_404_if_unsafe_next_url(client):
    url = reverse("magicauth-login")
    response = client.get(url, {"next": "http://www.myfishingsite.com/"})
    assert response.status_code == 404


def test_login_page_raises_404_if_unsafe_next_url_with_authenticated_user(client):
    user = factories.UserFactory()
    client.force_login(user)
    url = reverse("magicauth-login")
    response = client.get(url, {"next": "http://www.myfishingsite.com/"})
    assert user.is_authenticated
    assert response.status_code == 404

def test_template_displays_totp_field_when_2FA_enabled(client):
    settings.ENABLE_2FA = True
    response = client.get(reverse("magicauth-login"))
    assert response.status_code == 200
    assert "Entrez le code à 6" in response.rendered_content

def test_template_does_not_displays_totp_field_when_2FA_disabled(client):
    settings.ENABLE_2FA = False
    response = client.get(reverse("magicauth-login"))
    assert response.status_code == 200
    assert "Entrez le code" not in response.rendered_content
