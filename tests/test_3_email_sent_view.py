from pytest import mark

from django.shortcuts import reverse
from tests import factories

'''
Step 3 of login process : see doc in magicauth/views.py for step details
'''

pytestmark = mark.django_db


def test_email_sent_page_loads(client):
    url = reverse("magicauth-email-sent")
    response = client.get(url)
    assert response.status_code == 200


def test_email_sent_page_raises_404_if_unsafe_next_url(client):
    url = reverse("magicauth-email-sent") + "?next=http://www.myfishingsite.com/"
    response = client.get(url)
    assert response.status_code == 404


def test_email_sent_page_raises_404_if_unsafe_next_url_with_authenticated_user(client):
    user = factories.UserFactory()
    client.force_login(user)
    url = reverse("magicauth-email-sent") + "?next=http://www.myfishingsite.com/"
    response = client.get(url)
    assert response.status_code == 404
    assert user.is_authenticated
