from datetime import timedelta
from pytest import mark
import urllib.parse

from django.shortcuts import reverse
from django.utils import timezone
from magicauth.models import MagicToken
from magicauth import settings
from tests import factories

'''
Step 5 of login process : see doc in magicauth/views.py for step details
'''

pytestmark = mark.django_db


def open_magic_link(client, token, next=None):
    url = reverse("magicauth-validate-token", args=[token.key])
    if next:
        # Encode the url (with urllib.parse.quote) otherwise URL params get lost.
        url += '?next=' + urllib.parse.quote(next)
    return client.get(url)


def test_opening_magic_link_triggers_login(client):
    token = factories.MagicTokenFactory()
    open_magic_link(client, token)
    assert "_auth_user_id" in client.session


def test_opening_magic_link_with_valid_token_redirects(client):
    token = factories.MagicTokenFactory()
    response = open_magic_link(client, token)
    assert response.status_code == 302
    assert response.url == "/landing/"


def test_opening_magic_link_with_a_next_sets_a_new_url(client):
    token = factories.MagicTokenFactory()
    next_url_raw = "/test_dashboard/?a=test&b=test"
    response = open_magic_link(client, token, next_url_raw)
    assert response.status_code == 302
    assert response.url == next_url_raw


def test_validate_token_view_with_unsafe_next_does_not_log_in(client):
    token = factories.MagicTokenFactory()
    next_url = 'http://www.myfishingsite.com/'
    open_magic_link(client, token, next_url)
    assert "_auth_user_id" not in client.session


def test_validate_token_view_with_unsafe_next_raises_404(client):
    token = factories.MagicTokenFactory()
    next_url = 'http://www.myfishingsite.com/'
    response = open_magic_link(client, token, next_url)
    assert response.status_code == 404


def test_validate_token_view_with_unsafe_next_raises_404_for_loggedin_user(client):
    token = factories.MagicTokenFactory()
    user = factories.UserFactory()
    client.force_login(user)
    next_url = 'http://www.myfishingsite.com/'
    response = open_magic_link(client, token, next_url)
    assert response.status_code == 404
    assert user.is_authenticated


def test_token_is_removed_after_visiting_magic_link(client):
    token = factories.MagicTokenFactory()
    count_before = MagicToken.objects.count()
    open_magic_link(client, token)
    count_after = MagicToken.objects.count()
    assert count_after == count_before - 1


def test_duplicate_token_for_same_user_is_removed_after_visiting_magic_link(client):
    token = factories.MagicTokenFactory()
    duplicate = factories.MagicTokenFactory(user=token.user)
    open_magic_link(client, token)
    assert duplicate not in MagicToken.objects.all()


def test_unknown_token_does_not_login(client):
    url = reverse("magicauth-validate-token", args=["unknown-token"])
    client.get(url)
    assert "_auth_user_id" not in client.session


def test_unknown_token_redirects_to_login(client):
    url = reverse("magicauth-validate-token", args=["unknown-token"])
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == '/login/'


def create_expired_token():
    token = factories.MagicTokenFactory()
    token.created = timezone.now() - timedelta(seconds=(settings.TOKEN_DURATION_SECONDS * 2))
    token.save()
    return token


def test_expired_token_does_not_login(client):
    token = create_expired_token()
    open_magic_link(client, token)
    assert "_auth_user_id" not in client.session


def test_expired_token_redirects_to_login(client):
    token = create_expired_token()
    response = open_magic_link(client, token)
    assert response.status_code == 302
    assert response.url == '/login/'


def test_expired_token_is_deleted_when_visited(client):
    token = create_expired_token()
    open_magic_link(client, token)
    assert token not in MagicToken.objects.all()


def test_expired_token_is_deleted_when_valid_token_is_visited(client):
    expired_token = create_expired_token()
    valid_token = factories.MagicTokenFactory(user=expired_token.user)
    open_magic_link(client, valid_token)
    assert expired_token not in MagicToken.objects.all()
