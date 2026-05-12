from django.utils.translation import gettext

from jdash.config.textmessages import TextMessages as textmessages


def controller_error_message(exc):
    """
    Build a user-facing support message for controller-level exceptions.

    Args:
        exc (Exception): The exception that was raised.

    Returns:
        str: Formatted error message safe to place into context.
    """
    return f"{exc} : {gettext(textmessages.error_message_to_contact_support)}"
