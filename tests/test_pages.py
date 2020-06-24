from datetime import timedelta
from pytest import mark
import urllib.parse

from django.core import mail
from django.shortcuts import reverse
from django.utils import timezone
from magicauth.models import MagicToken
from magicauth import settings
from tests import factories

pytestmark = mark.django_db


#########################
# Step 1 : GET LoginView
#########################


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


#########################################
# Step 2 : POST your email to LoginView
#########################################


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


###################################################
# Step 3 : email-sent page
###################################################


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


###################################################
# Step 4 : click (GET) the link received by email
###################################################

# Option A : no wait page

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


# Option B : with wait page


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
