from datetime import timedelta
from pytest import mark

from django.core import mail
from django.shortcuts import reverse
from django.utils import timezone

from magicauth.models import MagicToken
from tests import factories

pytestmark = mark.django_db


def test_getting_LoginView_while_authenticated_redirects_to_default(client):
    user = factories.UserFactory()
    client.force_login(user)
    url = reverse("magicauth-login")
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == "/test_home/"


def test_getting_LoginView_while_authenticated_with_next_redirects_to_next(client):
    user = factories.UserFactory()
    client.force_login(user)
    url = reverse("magicauth-login") + "?next=/test_dashboard/"
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == "/test_dashboard/"


def test_posting_email_for_valid_existing_user_redirects(client):
    user = factories.UserFactory()
    url = reverse("magicauth-login")
    data = {"email": user.email}
    response = client.post(url, data=data)
    assert response.status_code == 302
    assert len(mail.outbox) == 1


def test_loging_with_email_is_case_insensitive(client):
    user = factories.UserFactory()
    url = reverse("magicauth-login")
    data = {"email": user.email.upper()}
    response = client.post(url, data=data)
    assert response.status_code == 302
    assert len(mail.outbox) == 1


def test_posting_unknown_email_raise_error(client):
    url = reverse("magicauth-login")
    data = {"email": "unknown@email.com"}
    response = client.post(url, data=data)
    assert "invalid" in str(response.content)
    assert len(mail.outbox) == 0


def test_posting_email_for_valid_existing_user_sends_email(client):
    user = factories.UserFactory()
    url = reverse("magicauth-login")
    data = {"email": user.email}
    client.post(url, data=data)
    assert len(mail.outbox) == 1
    assert "?next=/test_home/" in mail.outbox[0].body


def test_posting_email_redirect_to_default_view(client):
    user = factories.UserFactory()
    url = reverse("magicauth-login")
    data = {"email": user.email}
    client.post(url, data=data)
    assert "?next=/test_home/" in mail.outbox[0].body


def test_posting_email_with_next_redirects_to_next(client):
    user = factories.UserFactory()
    url = reverse("magicauth-login") + "?next=/test_dashboard/"
    data = {"email": user.email}
    client.post(url, data=data)
    assert "?next=/test_dashboard/" in mail.outbox[0].body


def test_posting_unknown_email_does_not_send_email(client):
    url = reverse("magicauth-login")
    data = {"email": "unknown@email.com"}
    client.post(url, data=data)
    assert len(mail.outbox) == 0


def test_posting_email_for_valid_existing_user_created_token(client):
    user = factories.UserFactory()
    url = reverse("magicauth-login")
    data = {"email": user.email}
    count_before = MagicToken.objects.count()
    client.post(url, data=data)
    count_after = MagicToken.objects.count()
    assert count_after == count_before + 1


def test_opening_magic_link_with_valid_token_redirects(client):
    token = factories.MagicTokenFactory()
    url = reverse("magicauth-validate-token", args=[token.key])
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == "/test_home/"


def test_opening_magic_link_with_a_next_sets_a_new_url(client):
    token = factories.MagicTokenFactory()
    url = (
        reverse("magicauth-validate-token", kwargs={"key": token.key})
        + "?next=/test_dashboard/?a=test&b=test"
    )
    response = client.get(url)
    assert response.status_code == 302
    assert response.url == "/test_dashboard/?a=test&b=test"


def test_opening_magic_link_with_a_unsafe_next_sets_triggers_404(client):
    token = factories.MagicTokenFactory()
    url = (
        reverse("magicauth-validate-token", kwargs={"key": token.key})
        + "?next=http://www.myfishingsite.com/?a=test&b=test"
    )
    response = client.get(url)
    assert response.status_code == 404


def test_opening_magic_link_with_a_unsafe_next_while_loggedin_sets_triggers_404(client):
    token = factories.MagicTokenFactory()
    user = factories.UserFactory()
    client.force_login(user)
    url = (
        reverse("magicauth-validate-token", kwargs={"key": token.key})
        + "?next=http://www.myfishingsite.com/?a=test&b=test"
    )
    response = client.get(url)
    assert response.status_code == 404
    assert user.is_authenticated == True


def test_token_is_removed_after_visiting_magic_link(client):
    token = factories.MagicTokenFactory()
    url = reverse("magicauth-validate-token", args=[token.key])
    count_before = MagicToken.objects.count()
    client.get(url)
    count_after = MagicToken.objects.count()
    assert count_after == count_before - 1


def test_duplicate_token_for_same_user_is_removed_after_visiting_magic_link(client):
    token = factories.MagicTokenFactory()
    duplicate = factories.MagicTokenFactory(user=token.user)
    url = reverse("magicauth-validate-token", args=[token.key])
    client.get(url)
    assert duplicate not in MagicToken.objects.all()


def test_visiting_magic_link_triggers_login(client):
    token = factories.MagicTokenFactory()
    url = reverse("magicauth-validate-token", args=[token.key])
    client.get(url)
    assert "_auth_user_id" in client.session


def test_unknown_token_redirects(client):
    url = reverse("magicauth-validate-token", args=["unknown-token"])
    response = client.get(url)
    assert response.status_code == 302


def test_expired_token_redirects(client):
    token = factories.MagicTokenFactory()
    token.created = timezone.now() - timedelta(days=1)
    token.save()
    url = reverse("magicauth-validate-token", args=[token.key])
    response = client.get(url)
    assert response.status_code == 302


def test_expired_token_is_deleted(client):
    token = factories.MagicTokenFactory()
    token.created = timezone.now() - timedelta(days=1)
    token.save()
    url = reverse("magicauth-validate-token", args=[token.key])
    client.get(url)
    assert token not in MagicToken.objects.all()
