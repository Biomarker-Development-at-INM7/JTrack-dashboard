import pytest
from django.urls import reverse
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_login_valid(client):
    User.objects.create_user(username='testuser', password='testpass')
    response = client.post(reverse('login'), {'username': 'testuser', 'password': 'testpass'})
    assert response.status_code == 302
    assert response.url == reverse('home')

@pytest.mark.django_db
def test_login_invalid(client):
    response = client.post(reverse('login'), {'username': 'wrong', 'password': 'wrong'})
    assert response.status_code == 200
    assert "Invalid username or password." in response.content.decode()