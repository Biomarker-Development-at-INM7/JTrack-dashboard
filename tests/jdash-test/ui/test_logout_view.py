import pytest
from django.test import Client
from django.urls import reverse
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_logout(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.login(username='testuser', password='testpass')
    response = client.post(reverse('logout'))
    assert response.status_code == 302
    assert response.url == reverse('login')


@pytest.mark.django_db
def test_logout_rejects_get(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.login(username='testuser', password='testpass')

    response = client.get(reverse('logout'))

    assert response.status_code == 405
    assert '_auth_user_id' in client.session


@pytest.mark.django_db
def test_logout_requires_csrf_token():
    user = User.objects.create_user(username='testuser', password='testpass')
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)

    rejected_response = client.post(reverse('logout'))

    assert rejected_response.status_code == 302
    assert rejected_response.url == '/login/'
    assert '_auth_user_id' in client.session

    profile_response = client.get(reverse('profile'))
    csrf_token = profile_response.cookies['csrftoken'].value
    accepted_response = client.post(
        reverse('logout'),
        HTTP_X_CSRFTOKEN=csrf_token,
    )

    assert accepted_response.status_code == 302
    assert accepted_response.url == reverse('login')
    assert '_auth_user_id' not in client.session
