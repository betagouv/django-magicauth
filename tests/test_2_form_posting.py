from pytest import mark

from django.core import mail
from django.shortcuts import reverse
from magicauth.models import MagicToken
from tests import factories

'''
Step 2 of login process : see doc in magicauth/views.py for step details
'''

pytestmark = mark.django_db


def post_email(client, email):
    url = reverse("magicauth-login")
    return client.post(url, data={"email": email})


def test_posting_email_for_valid_existing_user_redirects(client):
    user = factories.UserFactory()
    response = post_email(client, user.email)
    assert response.status_code == 302


def test_posting_email_for_valid_existing_user_sends_email(client):
    user = factories.UserFactory()
    post_email(client, user.email)
    assert len(mail.outbox) == 1


def test_posting_email_sends_email_with_redirection_to_default(client):
    user = factories.UserFactory()
    post_email(client, user.email)
    assert "?next=/landing/" in mail.outbox[0].body


def test_posting_email_sends_email_with_redirection_to_next(client):
    user = factories.UserFactory()
    url = reverse("magicauth-login") + "?next=/test_dashboard/"
    client.post(url, data={"email": user.email})
    assert "?next=/test_dashboard/" in mail.outbox[0].body


def test_posting_email_with_usafe_next_does_not_send_email_and_returns_404(client):
    user = factories.UserFactory()
    url = reverse("magicauth-login") + "?next=http://www.myfishingsite.com/"
    response = client.post(url, data={"email": user.email})
    assert len(mail.outbox) == 0
    assert response.status_code == 404


def test_posting_email_for_valid_existing_user_creates_token(client):
    user = factories.UserFactory()
    count_before = MagicToken.objects.count()
    post_email(client, user.email)
    count_after = MagicToken.objects.count()
    assert count_after == count_before + 1


def test_loging_with_email_is_case_insensitive(client):
    user = factories.UserFactory()
    response = post_email(client, user.email.upper())
    assert response.status_code == 302
    assert len(mail.outbox) == 1


def test_posting_unknown_email_raise_error(client):
    response = post_email(client, "unknown@email.com")
    assert "invalid" in str(response.content)


def test_posting_unknown_email_does_not_send_email(client):
    post_email(client, "unknown@email.com")
    assert len(mail.outbox) == 0
