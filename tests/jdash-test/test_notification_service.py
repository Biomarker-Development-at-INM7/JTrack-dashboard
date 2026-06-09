# --- Environment Setup ---
import os
import sys

# Ensure the project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Set the Django settings module BEFORE importing Django stuff
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin.settings")

# Setup Django
import django
django.setup()

# --- Django ---
from django.utils import timezone
from django.http import HttpResponse
from django.contrib.auth.models import User, Group, Permission

# --- Third-party ---
import pytest
from unittest.mock import MagicMock, patch, mock_open

# --- Standard Library ---


# --- Local Imports ---
# Do this AFTER django.setup()
from jdash.services import notification


@patch("google.auth.transport.requests.Request")
def test_get_access_token_refresh(mock_request):
    mock_cred = MagicMock()
    mock_cred.valid = False
    mock_cred.token = "refreshed_token"

    def refresh_side_effect(req):
        mock_cred.token = "refreshed_token"
    mock_cred.refresh.side_effect = refresh_side_effect

    token = notification.get_access_token(mock_cred)

    # Check refresh call args type
    assert mock_cred.refresh.call_count == 1
    args, _ = mock_cred.refresh.call_args
    assert args[0].__class__.__name__ == "Request"
    assert token == "refreshed_token"


def test_get_access_token_valid():
    mock_cred = MagicMock()
    mock_cred.valid = True
    mock_cred.token = "valid_token"
    token = notification.get_access_token(mock_cred)
    assert token == "valid_token"


@patch("jdash.services.notification.requests.post")
@patch("builtins.open", new_callable=mock_open, read_data='{"pushNotification_token":"token123","deviceBrand":"Android"}')
@patch("json.load")
@patch("google.oauth2.service_account.Credentials.from_service_account_file")
@patch("jdash.services.notification.get_access_token")
@patch("jdash.services.notification.get_receivers_tokens")
@patch("jdash.services.notification.push_notification")
def test_send_push_notification_all_variants(
    mock_push_notification,
    mock_get_receivers_tokens,
    mock_get_access_token,
    mock_cred_file,
    mock_json_load,
    mock_open_file,
    mock_requests_post,
):
    # Setup mocks
    mock_cred = MagicMock()
    mock_cred.valid = True
    mock_cred.token = "token"
    mock_cred_file.return_value = mock_cred
    mock_get_access_token.return_value = "token"

    # Receiver JSON loader returns deviceBrand 'Android' for main modality
    mock_json_load.return_value = {
        "pushNotification_token": "token123",
        "deviceBrand": "Android",
        "deviceBrand_ema": "iOS",
    }

    # Return tokens and no errors
    mock_get_receivers_tokens.return_value = (["token123"], [])

    # push_notification returns success string
    mock_push_notification.return_value = "success"

    receivers = [
        "subject1:main",
        "subject2:ema",
    ]
    study_id = "studyX"

    errors = notification.send_push_notification("Title", "Body", receivers, study_id)

    assert mock_get_access_token.call_count == 2
    assert mock_get_receivers_tokens.call_count == 2
    assert mock_push_notification.call_count == 2
    assert isinstance(errors, list)
    assert errors == ["success", "success"]


@patch("jdash.services.notification.requests.post")
def test_push_notification_sends_post(mock_post):
    mock_post.return_value.text = "OK"
    result = notification.push_notification(
        title="Test",
        text="Body",
        tokens_auth=["token1", "token2"],
        headers={"Authorization": "Bearer token"},
        deviceBrand="Android",
        ids="subject1",
        url="http://fake.url",
    )
    mock_post.assert_called_once()
    called_args, called_kwargs = mock_post.call_args
    assert called_kwargs["json"]["message"]["notification"]["title"] == "Test"
    assert result.startswith("OK")
    assert "subject1" in result
    assert "Android" in result


@patch("builtins.open", new_callable=mock_open, read_data='{"pushNotification_token":"token123","pushNotification_token_ema":"token456"}')
@patch("json.load")
def test_get_receivers_tokens_main_and_ema(mock_json_load, mock_open_file):
    # Main modality token
    mock_json_load.return_value = {
        "pushNotification_token": "token_main",
        "deviceBrand": "Android"
    }
    token, errors = notification.get_receivers_tokens("subject1", "study1", notification.constants.main)
    assert token == "token_main"
    assert errors == []

    # EMA modality token present as pushNotification_token_ema
    mock_json_load.return_value = {
        "pushNotification_token_ema": "token_ema"
    }
    token, errors = notification.get_receivers_tokens("subject1", "study1", notification.constants.ema)
    assert token == "token_ema"
    assert errors == []

    # EMA modality token falls back to pushNotification_token
    mock_json_load.return_value = {
        "pushNotification_token": "token_ema_fallback"
    }
    token, errors = notification.get_receivers_tokens("subject1", "study1", notification.constants.ema)
    assert token == "token_ema_fallback"
    assert errors == []

    # Missing tokens
    mock_json_load.return_value = {}
    token, errors = notification.get_receivers_tokens("subject1", "study1", "unknown_modality")
    assert token == ""
    assert errors != []


def test_generate_verification_code_range():
    for _ in range(100):
        code = notification.generate_verification_code()
        assert 100000 <= code <= 999999


@patch("jdash.services.notification.smtplib.SMTP")
@patch("jdash.services.notification.render_to_string")
@patch("jdash.services.notification.add_verification_code")
def test_send_email_various_links(mock_add_ver_code, mock_render, mock_smtp):
    # Setup mocks
    mock_render.side_effect = lambda template, ctx: f"Rendered {template} with {ctx}"
    mock_smtp_instance = mock_smtp.return_value
    mock_smtp_instance.sendmail.return_value = {}

    # Test https link triggers download link email
    result = notification.send_email("John Doe", "john@example.com", "msg", "https://downloadlink")
    assert result is True
    mock_render.assert_called_with(notification.constants.download_link, {"download_link": "https://downloadlink"})

    # Test confirm link triggers verification code email and add_verification_code called
    result = notification.send_email("John Doe", "john@example.com", "msg", "confirm")
    assert result is True
    mock_add_ver_code.assert_called_once()

    # Test delete_subject triggers special email
    result = notification.send_email("John Doe", "john@example.com", "delete subject data", "delete_subject")
    assert result is True

    # Test default case
    result = notification.send_email("John Doe", "john@example.com", "Inquiry message", "other")
    assert result is True

    # Test SMTP failure
    mock_smtp_instance.sendmail.side_effect = Exception("SMTP error")
    result = notification.send_email("John Doe", "john@example.com", "msg", "https://downloadlink")
    assert result is False