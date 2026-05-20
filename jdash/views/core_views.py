import logging

from django.conf import settings
from django.contrib import messages, auth
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect, render

from jdash.services.notification import send_email
from jdash.services.study import get_all_study_details
from jdash.forms import ContactUsForm
from jdash.config import constants as constants
from jdash.services.datahelper import get_contactus_form_data
from jdash.repositories.study_repository import get_group_name_for_user
from jdash.interface.session_manager import SessionManager
from jdash.config.textmessages import TextMessages as textmessages

logger = logging.getLogger("django")


def server_error(request, template_name='500.html'):
    """
    Handles server error (HTTP 500) responses.

    This view is used by Django's error handling flow to render the configured
    500 template and log the failing request path for diagnostics.

    Args:
        request (HttpRequest): The HTTP request object.
        template_name (str, optional): Template used for the response.

    Returns:
        HttpResponse: Rendered 500 page with a 500 status code.
    """
    logger.exception("Server error occurred for %s", request.path)
    return render(request, template_name, status=500)


@login_required
def session_check(request):
    """
    Checks whether the current authenticated session is still active.

    Returns:
        JsonResponse: JSON payload with an ``active`` flag.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"active": False}, status=401)

    if request.GET.get("refresh") == "1":
        session_age = getattr(settings, "SESSION_COOKIE_AGE", None)
        if session_age:
            request.session.set_expiry(session_age)
        request.session.modified = True

    return JsonResponse({"active": True})


@login_required
def index(request):
    """
    Renders the home page with study metadata and dashboard statistics.

    This view loads study details from session cache when available and
    refreshes them for the authenticated user when needed.

    Returns:
        HttpResponse: Home page, login page, or error page.
    """
    context = {}
    if request.user.is_authenticated:
        logged_user = request.user
        study_meta = {}
        stats = {}
        error_message = ""
        try:
            user_detail = SessionManager.get_specific_session_data(
                request.session.session_key,
                constants.session_key_user_details,
                [],
            )
            logger.info("userdetail retrieving %s", user_detail)
            study_meta = SessionManager.get_specific_session_data(
                request.session.session_key,
                constants.session_key_studies,
                None,
            )
            stats = SessionManager.get_specific_session_data(
                request.session.session_key,
                constants.session_key_studies_stats,
                None,
            )

            if not study_meta:
                logger.info("storing values in session")
                study_meta, stats, error_message = get_all_study_details(logged_user)
                list_of_studies = {
                    study[constants.key_name_study_title]: study[constants.key_name_study_title]
                    for study in study_meta
                }
                cache.set(constants.session_key_list_studies, list_of_studies, timeout=3600)

                if not error_message:
                    session_studies_ema = request.session.get(constants.session_key_studies_ema, [])
                    session_old_studies_ema = request.session.get(constants.session_key_old_ema, [])
                    for study in study_meta:
                        sensor_list = study.get(constants.key_name_sensor_list) or []
                        if constants.ema in sensor_list:
                            session_studies_ema.append(study[constants.key_name_study_title])
                        if "old_ema" in study:
                            session_old_studies_ema.append(study[constants.key_name_study_title])
                    logger.info("ema studies %s", list(set(session_studies_ema)))
                    logger.info("old ema studies %s", list(set(session_old_studies_ema)))
                    request.session[constants.session_key_studies] = study_meta
                    request.session[constants.session_key_studies_stats] = stats
                    request.session[constants.session_key_studies_ema] = list(set(session_studies_ema))
                    request.session[constants.session_key_old_ema] = session_old_studies_ema
                    request.session.modified = True
                else:
                    return render(request, constants.error_page, context)
            else:
                logger.info("accessing values from session")
            context[constants.key_name_study_meta] = study_meta
            context[constants.key_name_stats] = stats
            messages.error(request, error_message)
            return render(request, constants.home_page, context)
        except Exception as e:
            logger.exception("Loading Home Page error")
            return render(request, constants.error_page, context)
    return render(request, constants.login_page)


def login_request(request):
    """
    Handles the login flow for the application.

    This view validates credentials, logs the user in, stores basic user
    details in the session, and redirects to the home page.

    Returns:
        HttpResponse: Redirect to home on success or login page on failure.
    """
    context = {}
    allowed_usernames = set(getattr(settings, "MAINTENANCE_ALLOWED_USERNAMES", []))

    if request.method == constants.post_method:
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get(constants.field_name_username)
            password = form.cleaned_data.get(constants.field_name_password)
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                request.session[constants.session_key_user_details] = {
                    constants.session_key_username: user.username,
                    constants.session_key_email: user.email,
                    constants.session_key_first_name: user.first_name,
                    constants.session_key_last_name: user.last_name,
                }
                request.session[constants.session_key_groupname] = get_group_name_for_user(user)
                request.session.modified = True
                if getattr(settings, "MAINTENANCE_MODE", False) and username not in allowed_usernames:
                    return redirect(constants.url_name_for_home)
                return redirect(constants.url_name_for_home)
            messages.error(request, textmessages.error_message_invalid_username_pswd)
        else:
            messages.error(request, textmessages.error_message_invalid_username_pswd)
    context[constants.key_name_login_form] = AuthenticationForm()
    context[constants.key_name_contact_form] = ContactUsForm()
    return render(request=request, template_name=constants.login_page, context=context)


def csrf_failure(request, reason=""):
    """
    Handles CSRF failures by redirecting the user back to login.

    Args:
        request (HttpRequest): The HTTP request object.
        reason (str, optional): Django-provided explanation for the failure.

    Returns:
        HttpResponseRedirect: Redirect response to the login page.
    """
    messages.error(request, "Session expired. Please log in again.")
    return redirect('/login/')


@login_required
def logout_request(request):
    """
    Handles the logout process for the current user.

    Returns:
        HttpResponseRedirect: Redirect response to the login page.
    """
    logout(request)
    auth.logout(request)
    return redirect(constants.url_name_for_login)


def contact_email(request):
    """
    Handles the contact email flow for the application.

    This view validates the submitted contact form, sends the message by
    email, and renders either a success page or the contact form again.

    Returns:
        HttpResponse: Success page or contact form page.
    """
    context = {}
    if constants.button_name_contact_message in request.POST:
        form = ContactUsForm(request.POST)
        logger.info(form.errors)
        if form.is_valid():
            fullname, sender_email, message = get_contactus_form_data(form)
            send_email(fullname, sender_email, message, "")
            context[constants.key_name_text_message] = textmessages.success_contacting_message
            return render(request, constants.success, context)
    context[constants.key_name_contact_form] = ContactUsForm()
    return render(request, constants.contact_us, context)
