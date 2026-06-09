import pytest
from jdash.config.textmessages import TextMessages

@pytest.fixture
def messages():
    return TextMessages()

def test_get_existing_message(messages):
    assert messages.get_message("success_new_user") == "New users have been successfully created."

def test_get_nonexistent_message(messages):
    assert messages.get_message("nonexistent_key") == "Message type not found."

def test_customize_message_valid(messages):
    messages.success_notification = "Hello, {name}!"
    assert messages.customize_message("success_notification", name="John") == "Hello, John!"

def test_customize_message_nonexistent(messages):
    result = messages.customize_message("nonexistent_key", key="value")
    assert result == "Message type not found."

def test_customize_message_missing_placeholder(messages):
    messages.success_notification = "Hello, {name}!"
    with pytest.raises(KeyError):
        messages.customize_message("success_notification")  # no `name` arg