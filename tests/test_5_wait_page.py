from pytest import mark

from django.shortcuts import reverse
from tests import factories


pytestmark = mark.django_db


def test_wait_page_raises_loads(client):
    url = reverse("magicauth-wait", kwargs={"key": 'some-token'})
    response = client.get(url)
    assert response.status_code == 200


def test_wait_page_raises_404_if_unsafe_next_url(client):
    token = factories.MagicTokenFactory()
    url = reverse("magicauth-wait", kwargs={"key": token.key})
    url += "?next=http://www.myfishingsite.com/"
    response = client.get(url)
    assert response.status_code == 404
