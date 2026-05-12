import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from jdash.services.controller import (
    download_subject_qr_file,
    dowload_unused_qr_code_files,
    initiate_download_study_dataset,
)
from jdash.services.notification import send_email
from jdash.forms import DeleteSubjectForm
from jdash.config import constants as constants
from jdash.repositories.study_repository import set_email_for_user
from jdash.config.textmessages import TextMessages as textmessages
from jdash.views.study_views import study_details

logger = logging.getLogger("django")


@login_required
def download_unused_files(request, arg):
    """
    Dispatches study-related download requests.

    This view handles subject QR downloads, dataset download initiation, and
    unused QR-sheet downloads from the study details page.

    Args:
        request (HttpRequest): The HTTP request object.
        arg (str): Selector for the type of download.

    Returns:
        HttpResponse: Download response, study details response, or error page.
    """
    try:
        if "00" in arg:
            return download_subject_qr_file(arg)
        if "data" in arg:
            data = request.POST
            logger.info("details from the request %s", data)
            user_details = request.session.get(constants.session_key_user_details, {})
            if user_details[constants.field_name_email] == '':
                user_details[constants.field_name_email] = data[constants.field_name_user_email]
                request.session[constants.session_key_user_details] = user_details
                request.session.modified = True
                set_email_for_user(
                    user_details[constants.field_name_username],
                    data[constants.field_name_user_email],
                )
            data_type = request.POST.get(constants.key_name_type, "processed")
            initiate_download_study_dataset(
                data[constants.key_name_study_name],
                data_type,
                user_details,
            )
            return study_details(request, data[constants.key_name_study_name])
        return dowload_unused_qr_code_files(arg)
    except Exception as e:
        logger.info("download_unused_files::Unexpected Error %s ", e)
        return render(request, constants.error_page, context={})

def delete_subject_data(request):
    """
    Handles public subject-data deletion requests.

    This view validates the deletion request form, sends the request by email,
    and renders either a success page or the form again.

    Returns:
        HttpResponse: Success page or delete-subject form page.
    """
    logger.info("delete_subject_data:::start")
    context = {}
    if constants.url_name_for_delete_subject_data in request.POST:
        form = DeleteSubjectForm(request.POST)
        if form.is_valid():
            selected_id = form.cleaned_data.get(constants.field_name_subjectId)
            email = form.cleaned_data.get(constants.field_name_email)
            reason = form.cleaned_data.get(constants.field_name_reason)
            send_email(selected_id, email, "", constants.url_name_for_delete_subject)
            context[constants.key_name_text_message] = textmessages.success_deletion_data_request
            logger.info("delete_subject_data: %s::end", email)
            return render(request, constants.success, context)
    context[constants.key_name_delete_subject_form] = DeleteSubjectForm()
    return render(request, constants.delete_subject, context)
