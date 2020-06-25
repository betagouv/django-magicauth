from pytest import mark

from django.shortcuts import reverse
from magicauth import settings
import urllib.parse
from tests import factories


'''
Step 4 of login process : see doc in magicauth/views.py for step details

Note : We do not test that the javascript actually does the redirect. We just test the django template's context.
'''

pytestmark = mark.django_db

def open_magic_link_with_wait(client, token, next=None):
    url = reverse("magicauth-wait", kwargs={"key": token.key})
    if next:
        # Encode the url (with urllib.parse.quote) otherwise URL params get lost.
        url += '?next=' + urllib.parse.quote(next)
    return client.get(url)


def test_wait_page_loads(client):
    url = reverse("magicauth-wait", kwargs={"key": 'some-token'})
    response = client.get(url)
    assert response.status_code == 200


def test_wait_page_will_redirect_to_validate_token(client):
    token = factories.MagicTokenFactory()
    response = open_magic_link_with_wait(client, token)

    redirect_url = reverse('magicauth-validate-token', kwargs={"key": token.key})
    assert redirect_url in response.context_data['next_step_url']


def test_wait_page_will_redirect_with_next_param(client):
    token = factories.MagicTokenFactory()
    response = open_magic_link_with_wait(client, token, '/test_dashboard/')

    assert 'next=/test_dashboard/' in response.context_data['next_step_url']


def test_wait_page_will_redirect_with_default_next_param(client):
    token = factories.MagicTokenFactory()
    response = open_magic_link_with_wait(client, token)

    assert 'next=/landing/' in response.context_data['next_step_url']


def test_wait_page_will_redirect_in_WAIT_SECONDS(client):
    token = factories.MagicTokenFactory()
    response = open_magic_link_with_wait(client, token)

    assert response.context_data['WAIT_SECONDS'] == settings.WAIT_SECONDS


def test_wait_page_raises_404_if_unsafe_next_url(client):
    token = factories.MagicTokenFactory()
    response = open_magic_link_with_wait(
        client, token, 'http://www.myfishingsite.com/')

    assert response.status_code == 404
