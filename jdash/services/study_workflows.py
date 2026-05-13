import csv
import json
import logging
import os
import shlex
import subprocess
import threading
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.http.response import FileResponse, Http404, HttpResponse
from django.urls import reverse
from django.utils.encoding import escape_uri_path
from django.utils.translation import gettext

from jdash.config import constants as constants
from jdash.config import runtime_config as config
from jdash.config.textmessages import TextMessages as textmessages
from jdash.exceptions.controllerexceptions import controller_error_message
from jdash.models import FileDownloadToken
from jdash.repositories.study_repository import (
    retrieve_study_details_by_title,
    retrieve_test_cases_for_study,
)
from jdash.services.context_builder import context_for_home_page
from jdash.services.datahelper import get_study_form_data
from jdash.services.notification import send_push_notification as send_push_notification_impl
from jdash.services.study import Study, get_all_study_details
from jdash.services.subject import Subject
from jdash.utils.fileutils import change_permissions, handle_uploaded_file, open_study_json, save_study_json
from jdash.utils.utils import study_name_user_id

logger = logging.getLogger("django")


def dowload_unused_qr_code_files(study_name):
    """
    Download unused QR code files for a study as a ZIP attachment.
    """
    try:
        zip_path = Study(study_name, None).zip_unused_sheets()
    except FileNotFoundError as exc:
        raise Http404(str(exc))

    if not os.path.exists(zip_path):
        raise Http404("ZIP file was not created.")

    file_handle = open(zip_path, "rb")
    response = FileResponse(file_handle, content_type=constants.zip_content_type)
    response["Content-Disposition"] = (
        f"attachment; filename*=utf-8''{escape_uri_path(os.path.basename(zip_path))}"
    )
    try:
        response["Content-Length"] = str(os.path.getsize(zip_path))
    except OSError:
        pass
    return response


def download_subject_qr_file(subject_id):
    """
    Return a subject QR PDF as a downloadable response.
    """
    study_name = subject_id.split(".")[0]
    filepath = os.path.join(
        settings.DASH_FOLDER,
        os.path.join(
            config.app_study_folder,
            study_name_user_id(study_name),
            config.sheets_folder,
            subject_id + constants.pdf_extension,
        ),
    )
    with open(filepath, "rb") as file_handle:
        response = HttpResponse(file_handle.read(), content_type=constants.pdf_content_type)
        response["Content-Disposition"] = (
            "attachment; filename=%s" % subject_id + constants.pdf_extension
        )
        return response


def download_dataset(study_dataset_name):
    """
    Stream a prepared study dataset ZIP back to the caller.
    """
    logger.info("final download_dataset %s", study_dataset_name)
    filepath = os.path.join(
        config.storage_folder,
        os.path.join(config.download_folder, study_dataset_name + constants.zip_extension),
    )
    response = FileResponse(
        open(filepath, "rb"),
        content_type=constants.zip_content_type,
        as_attachment=True,
        filename=study_dataset_name + constants.zip_extension,
    )
    response["Content-Disposition"] = (
        f"attachment; filename*=utf-8''"
        f"{escape_uri_path(study_dataset_name + constants.zip_extension)}"
    )
    response.set_cookie(
        "file_download_started",
        "1",
        max_age=60,
        samesite="Lax",
    )
    logger.info(response)
    return response


def initiate_download_study_dataset(study_name, data_type, user_details):
    """
    Start asynchronous dataset generation and follow-up email delivery.
    """
    logger.info("initiate_download_study_dataset::start %s %s", study_name,data_type)
    file_date_identifier = timezone.now().strftime("%Y-%m-%dT%H:%M:%S")
    # Build the SSH command to execute the remote script
    ssh_command = f"ssh {settings.REMOTE_USERNAME}@{settings.JUSELESS_SERVER} 'python3 {config.juseless_download_script_path} {study_name} {data_type} {file_date_identifier}'"
    executable_filepath = os.path.join(config.storage_folder, config.download_folder, "download_dataset.sh")
    try:
        with open(executable_filepath, 'a',encoding='utf-8') as jf:
                jf.write(ssh_command)
                jf.write("\n")

        filename = study_name + "_" + data_type + "_" + file_date_identifier
        logger.info("initiate_download_study_dataset::end %s", study_name)
        thread = threading.Thread(target=check_file_and_send_email, args=(user_details, filename))
        thread.start()
        return True
    except Exception as exc:
        logger.info("An error occurred: %s", exc)
        return False

def check_file_and_send_email(user_details, filename):
    """
    Generate a tokenized download link and log the request metadata.
    """
    _zip_filepath = os.path.join(config.storage_folder, config.download_folder, filename + ".zip")
    token_instance = FileDownloadToken.objects.create(
        first_name=user_details.get("first_name"),
        email=user_details.get("email"),
        file_name=filename,
        status="initiated",
        expiration_date=timezone.now() + timedelta(days=7),
    )
    link = "https://jdash.inm7.de" + reverse("download_dataset", args=[token_instance.token])
    token_instance.link = link
    token_instance.save()


def create_new_study(form, task_formset, request, study_device_formset, sensor_formsets):
    """
    Orchestrate creation of a new study from validated form inputs.
    """
    logger.info("add_study:start ")
    context = {}
    form_data = get_study_form_data(
        form,
        task_formset,
        request,
        study_device_formset,
        sensor_formsets,
    )
    form_data["version"] = 1
    logger.info("successful retrieval of form data %s", form_data)
    if form_data[constants.field_name_images] is True:
        handle_uploaded_file(
            request.FILES[constants.field_name_images_zip_file],
            form_data[constants.field_name_name],
        )

    study_service = Study(form_data[constants.field_name_name], request.user)
    study_service.meta = form_data
    try:
        study_service.create()
        response, error = True, ""
    except Exception as exc:
        logger.exception(
            "create_new_study failed for study=%s",
            form_data.get(constants.field_name_name),
        )
        response, error = False, controller_error_message(exc)

    logger.info("response after creating entries in db %s", response)
    if response:
        context = context_for_home_page(request.user)
        context[constants.key_name_success_message] = (
            form_data[constants.field_name_name] + " is succesfully created"
        )
    context[constants.key_name_error_message] = error
    return context


def update_study_meta_data(study_name, form, formset, request, study_device_formset, sensor_formsets):
    """
    Orchestrate update of an existing study from validated form inputs.
    """
    context = {}
    try:
        values_to_be_updated = get_study_form_data(
            form,
            formset,
            request,
            study_device_formset,
            sensor_formsets,
        )
        logger.info("update_study_meta_data %s", values_to_be_updated)
        Study(study_name, None).update(values_to_be_updated)
        context[constants.key_name_study_meta], context[constants.key_name_stats], error = (
            get_all_study_details(request.user)
        )
        context[constants.key_name_error_message] = error
    except Exception as exc:
        logger.exception("update_study_meta_data failed for study=%s", study_name)
        context = context_for_home_page(request.user)
        context[constants.key_name_error_message] = controller_error_message(exc)
    return context


def remove_subjects_from_study(study_name, subject_to_remove, context):
    """
    Mark a selected subject as removed within the in-memory study detail context.
    """
    logger.info("remove_subjects_from_study:start")

    try:
        subject_id_with_modality = str(subject_to_remove).split(constants.value_sep)[0]
        subject_id, app = subject_id_with_modality.split(constants.sep)
        group_id = subject_id.split("_")[0]
    except Exception as exc:
        logger.error("Failed to parse subject identifier '%s': %s", subject_to_remove, exc)
        return context

    group_subjects = context.get("d", {}).get(group_id)
    if group_subjects:
        for obj in group_subjects:
            if obj.get("subject_name") == subject_id and obj.get("app") == app:
                obj["status_code"] = 3
                context["success_message"] = f"{subject_id} has been succesfully removed"
    else:
        logger.warning("Group '%s' not found or is empty. Skipping status update.", group_id)

    try:
        context["subject_details"]["ids_to_be_removed"].remove(subject_to_remove)
    except ValueError:
        logger.warning("Subject '%s' not found in ids_to_be_removed.", subject_to_remove)

    logger.info("remove_subjects_from_study:end")
    if "success_message" not in context:
        context["success_message"] = f"{subject_id} not found but marked processed"
    return context

def create_subjects_for_study(study_name, count):
    """
    Create QR/PDF subject artifacts for a study and prepare success messaging.
    """
    logger.info("create_subjects:start")
    context = {}

    try:
        total_count = Subject.create_pdfs_for_study(study_name, count)

        study_json = open_study_json(study_name)
        study_json[constants.key_name_number_of_subjects] = total_count

        save_study_json(study_name, study_json)

        context[constants.key_name_meta_data] = study_json
        context[constants.key_name_success_message] = (
            str(count) + gettext(textmessages.success_new_user)
        )

    except Exception as exc:
        logger.exception("create_subjects_for_study failed for study=%s", study_name)
        context[constants.key_name_error_message] = controller_error_message(exc)

    logger.info("create_subjects:end")
    return context

def send_push_notification(study_name, message_title, message_text, receivers):
    """
    Send a push notification to the selected study receivers.
    """
    logger.info("send_notification ::start")
    context = {}
    try:
        errors = send_push_notification_impl(message_title, message_text, receivers, study_name)
        if len(errors) == 0:
            context[constants.key_name_success_message] = gettext(
                textmessages.success_notification
            )
        else:
            context[constants.key_name_error_message] = ", ".join(errors)
    except Exception as exc:
        logger.exception("send_push_notification failed for study=%s", study_name)
        context[constants.key_name_error_message] = controller_error_message(exc)

    logger.info("send_notification ::end")
    return context


def create_display_sop_list_of_study(study_name):
    """
    Build the SOP/QC display context for a study.
    """
    context = {}
    try:
        study = json.loads(retrieve_study_details_by_title(study_name))
        logger.info("create_display_sop_list_of_study %s", study)
        context[constants.key_name_test_list] = json.loads(
            retrieve_test_cases_for_study(study[constants.key_name_id])
        )
        if len(context[constants.key_name_test_list]) == 0:
            Study(study_name, None).create_test_cases()
            context[constants.key_name_test_list] = json.loads(
                retrieve_test_cases_for_study(study[constants.key_name_id])
            )
        context[constants.key_name_study] = study
    except Exception as exc:
        logger.exception("create_display_sop_list_of_study failed for study=%s", study_name)
        context[constants.key_name_study] = {constants.key_name_study_title: study_name}
        context[constants.key_name_test_list] = []
        context[constants.key_name_error_message] = controller_error_message(exc)
    return context


def close_study(study_name, user):
    """
    Close a study through the study service and reload the home-page data.
    """
    try:
        logger.info("Study %s is closed by %s", study_name, user.username)
        Study(study_name, user).close()
        return get_all_study_details(user)
    except Exception as exc:
        logger.exception("close_study failed for study=%s", study_name)
        return [], {}, controller_error_message(exc)


def delete_subjects_from_server(study_name, subject_ids):
    """
    Delete generated files for the selected subject ids from local storage.
    """
    from jdash.utils.fileutils import delete_user_files

    logger.info("delete_subjects_from_server subject  :start")
    for subject_id in subject_ids.split(constants.value_sep):
        subject_id = subject_id.strip()
        if not subject_id:
            logger.info("Skipped empty subject_id")
            continue
        logger.info("delete_subjects_from_server subject_id %s", subject_id)
        delete_user_files(study_name, subject_id)
    logger.info("delete_subjects_from_server subject  :end")
