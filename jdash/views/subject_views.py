import logging

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from jdash.services.controller import (
    download_subject_qr_file,
    dowload_unused_qr_code_files,
    initiate_download_study_dataset,
    generate_additional_subject_qr_codes,
)
from jdash.services.notification import send_email
from jdash.forms import DeleteSubjectForm
from jdash.config import constants as constants
from jdash.repositories.study_repository import is_test_study, set_email_for_user
from jdash.models import Study
from jdash.config.textmessages import TextMessages as textmessages
from jdash.views.study_views import study_details
from jdash.services.permissions import can_manage_study, can_manage_subjects, can_view_study
from jdash.views.message_helpers import forbidden_with_message

logger = logging.getLogger("django")


@login_required
@require_POST
def generate_additional_qr_codes(request, study_name):
    """Add activation QR codes 5–8 to selected subjects' existing PDFs."""
    if not can_manage_subjects(request.user, study_name):
        messages.error(request, "You do not have permission to generate additional QR codes.")
        return redirect(constants.url_name_for_details, study_name=study_name)

    subject_ids = list(dict.fromkeys(request.POST.getlist("subject_ids")))
    if not subject_ids:
        messages.error(request, "Select at least one subject.")
        return redirect(constants.url_name_for_details, study_name=study_name)

    generated_subjects = []
    failed_subjects = []
    for subject_id in subject_ids:
        try:
            generate_additional_subject_qr_codes(study_name, subject_id)
            generated_subjects.append(subject_id)
        except Exception:
            logger.exception(
                "Could not generate additional QR codes for study=%s subject=%s",
                study_name,
                subject_id,
            )
            failed_subjects.append(subject_id)

    if generated_subjects:
        messages.success(
            request,
            f"QR codes 5–8 were added to {len(generated_subjects)} subject PDF(s). "
            "Download the updated PDF using the Subject ID link in the table below.",
        )
    if failed_subjects:
        messages.error(
            request,
            "Additional QR codes could not be generated for: " + ", ".join(failed_subjects),
        )
    return redirect(constants.url_name_for_details, study_name=study_name)


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
            study_name = arg.split(".", 1)[0]
            study = Study.objects.filter(title=study_name, closed=False).first()
            if study is None or not can_view_study(request.user, study):
                return forbidden_with_message(
                    request,
                    "You do not have permission to download this subject QR code.",
                )
            return download_subject_qr_file(arg)
        if arg == "data":
            data = request.POST
            logger.info(
                "User action=request_dataset_download user=%s study=%s",
                request.user.get_username(),
                data.get(constants.key_name_study_name, ""),
            )
            logger.debug("download_unused_files request_data=%s", data)
            study_name = data.get(constants.key_name_study_name, "")
            study = Study.objects.filter(title=study_name, closed=False).first()
            if study is None or not can_manage_study(request.user, study):
                return forbidden_with_message(
                    request,
                    "You do not have permission to download data from this study.",
                )
            user_details = request.session.get(constants.session_key_user_details, {})
            if user_details[constants.field_name_email] == '':
                user_details[constants.field_name_email] = data[constants.field_name_user_email]
                request.session[constants.session_key_user_details] = user_details
                request.session.modified = True
                set_email_for_user(
                    user_details[constants.field_name_username],
                    data[constants.field_name_user_email],
                )
            data_type = (
                "raw"
                if is_test_study(study_name)
                else request.POST.get(constants.key_name_type, "processed")
            )
            download_queued = initiate_download_study_dataset(
                study_name,
                data_type,
                user_details,
            )
            if download_queued:
                messages.success(
                    request,
                    "The dataset is being prepared. A download link will be sent by email.",
                    fail_silently=True,
                )
            else:
                messages.error(
                    request,
                    "The dataset download could not be started. Select raw or processed data and try again.",
                    fail_silently=True,
                )
            return study_details(request, study_name)
        study = Study.objects.filter(title=arg, closed=False).first()
        if study is None or not can_view_study(request.user, study):
            return forbidden_with_message(
                request,
                "You do not have permission to download QR codes for this study.",
            )
        return dowload_unused_qr_code_files(arg)
    except Exception as e:
        logger.exception("download_unused_files::Unexpected Error %s", e)
        messages.error(
            request,
            "The requested download could not be prepared. Please try again.",
            fail_silently=True,
        )
        return render(request, constants.error_page, context={})

def delete_subject_data(request):
    """
    Handles public subject-data deletion requests.

    This view validates the deletion request form, sends the request by email,
    and renders either a success page or the form again.

    Returns:
        HttpResponse: Success page or delete-subject form page.
    """
    logger.debug("delete_subject_data request started")
    context = {}
    if constants.url_name_for_delete_subject_data in request.POST:
        form = DeleteSubjectForm(request.POST)
        if form.is_valid():
            selected_id = form.cleaned_data.get(constants.field_name_subjectId)
            email = form.cleaned_data.get(constants.field_name_email)
            reason = form.cleaned_data.get(constants.field_name_reason)
            send_email(selected_id, email, "", constants.url_name_for_delete_subject)
            messages.success(request, textmessages.success_deletion_data_request)
            context[constants.key_name_text_message] = textmessages.success_deletion_data_request
            logger.info("Public action=request_subject_data_deletion submitted=true")
            logger.debug("delete_subject_data request email=%s subject_id=%s", email, selected_id)
            return render(request, constants.success, context)
        else:
            messages.error(request, "Please correct the highlighted fields and submit the request again.")
    context[constants.key_name_delete_subject_form] = DeleteSubjectForm()
    return render(request, constants.delete_subject, context)
