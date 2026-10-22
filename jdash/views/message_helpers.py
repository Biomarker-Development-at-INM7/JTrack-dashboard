from django.contrib import messages
from django.shortcuts import render

from jdash.config import constants


DEFAULT_PERMISSION_MESSAGE = "You do not have permission to perform this action."


def add_context_messages(request, context, *, success=None, error=None):
    """Turn workflow context results into consistently styled Django messages."""
    context = context or {}
    error_text = error or context.get(constants.key_name_error_message)
    if error_text:
        messages.error(request, error_text)
    else:
        success_text = success or context.get(constants.key_name_success_message)
        if success_text:
            messages.success(request, success_text)
    return context


def add_form_error(request, action="save these changes"):
    messages.error(request, f"Please correct the highlighted fields and {action} again.")


def forbidden_with_message(request, message=DEFAULT_PERMISSION_MESSAGE):
    """Render the shared error page so a permission denial is visible as a popup."""
    messages.error(request, message)
    return render(request, constants.error_page, status=403)
