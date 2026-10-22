import pytest
from django.contrib.auth.models import User
from django.urls import reverse


@pytest.mark.django_db
def test_profile_requires_login(client):
    response = client.get(reverse("profile"))

    assert response.status_code == 302
    assert reverse("login") in response.url


@pytest.mark.django_db
def test_password_change_updates_password_and_keeps_session(client):
    user = User.objects.create_user(username="password-user", password="Old-password-123")
    client.force_login(user)

    response = client.post(
        reverse("profile"),
        {
            "old_password": "Old-password-123",
            "new_password1": "New-password-456",
            "new_password2": "New-password-456",
        },
    )

    assert response.status_code == 302
    assert response.url == f'{reverse("profile")}?tab=profile'
    user.refresh_from_db()
    assert user.check_password("New-password-456")
    assert client.session.get("_auth_user_id") == str(user.pk)


@pytest.mark.django_db
def test_password_change_rejects_incorrect_current_password(client):
    user = User.objects.create_user(username="password-user", password="Old-password-123")
    client.force_login(user)

    response = client.post(
        reverse("profile"),
        {
            "old_password": "incorrect",
            "new_password1": "New-password-456",
            "new_password2": "New-password-456",
        },
    )

    assert response.status_code == 200
    assert response.context["form"].errors["old_password"]
    user.refresh_from_db()
    assert user.check_password("Old-password-123")
