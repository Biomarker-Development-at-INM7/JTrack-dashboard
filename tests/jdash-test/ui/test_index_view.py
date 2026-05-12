import pytest
from django.urls import reverse
from django.contrib.auth.models import User

@pytest.mark.django_db
def test_index_authenticated(client):
    user = User.objects.create_user(username='testuser', password='testpass')
    client.login(username='testuser', password='testpass')
    response = client.get(reverse('home'))
    assert response.status_code == 200
    assert "text/html" in response["Content-Type"]

@pytest.mark.django_db
def test_index_unauthenticated(client):
    response = client.get(reverse('home'))
    assert response.status_code == 302
    assert '/login/' in response.url