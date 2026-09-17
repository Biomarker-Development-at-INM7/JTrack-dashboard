import csv
import json
import logging
import os
import shlex
import subprocess
import threading
import zipfile
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
    is_test_study,
    retrieve_study_details_by_title,
    retrieve_test_cases_for_study,
)
from jdash.services.context_builder import context_for_home_page
from jdash.services.datahelper import get_study_form_data
from jdash.services.notification import (
    send_email,
    send_push_notification as send_push_notification_impl,
)
from jdash.services.study import Study, get_all_study_details
from jdash.services.subject import Subject
from jdash.utils.fileutils import (
    change_permissions,
    delete_download_dataset_zip,
    handle_uploaded_file,
    open_study_json,
    save_study_json,
    set_download_file_permissions,
)
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
    if not os.path.exists(filepath):
        raise Http404("Requested dataset ZIP is no longer available.")

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
    response_close = response.close
    cleanup_done = False
    cleanup_remote = True
    filename_parts = study_dataset_name.rsplit("_", 2)
    if len(filename_parts) == 3 and filename_parts[1] in {"raw", "processed"}:
        try:
            cleanup_remote = not is_test_study(filename_parts[0])
        except Exception:
            logger.exception(
                "Could not determine dataset cleanup source for %s",
                study_dataset_name,
            )

    def close_with_zip_cleanup():
        nonlocal cleanup_done
        try:
            response_close()
        finally:
            if cleanup_done:
                return
            cleanup_done = True
            delete_download_dataset_zip(
                filepath,
                study_dataset_name,
                delete_remote=cleanup_remote,
            )

    response.close = close_with_zip_cleanup
    logger.info(response)
    return response


def download_study_dashboard_csv(study_name):
    """Stream the generated dashboard CSV for a study."""
    filename = f"{config.csv_prefix}{study_name}.csv"
    filepath = os.path.join(config.storage_folder, filename)
    if not os.path.isfile(filepath):
        raise Http404("Dashboard CSV is not available for this study.")

    return FileResponse(
        open(filepath, "rb"),
        content_type="text/csv; charset=utf-8",
        as_attachment=True,
        filename=filename,
    )


def initiate_download_study_dataset(study_name, data_type, user_details):
    """
    Start asynchronous dataset generation and follow-up email delivery.
    """
    try:
        test_study = is_test_study(study_name)
        if test_study:
            data_type = "raw"

        logger.info(
            "initiate_download_study_dataset::start %s %s",
            study_name,
            data_type,
        )
        if data_type not in {"raw", "processed"}:
            logger.warning("Unsupported study dataset type: %s", data_type)
            return False

        file_date_identifier = timezone.now().strftime("%Y-%m-%dT%H:%M:%S")
        filename = study_name + "_" + data_type + "_" + file_date_identifier
        if test_study:
            thread = threading.Thread(
                target=create_local_test_study_dataset,
                args=(study_name, data_type, filename, user_details),
            )
            thread.start()
            logger.info(
                "Queued local dataset generation for test study %s", study_name
            )
            return True

        # Non-test studies continue through the remote JUsless exporter.
        ssh_command = f"ssh {settings.REMOTE_USERNAME}@{settings.JUSELESS_SERVER} 'python3 {config.juseless_download_script_path} {study_name} {data_type} {file_date_identifier}'"
        executable_filepath = os.path.join(
            config.storage_folder,
            config.download_folder,
            "download_dataset.sh",
        )
        with open(executable_filepath, 'a',encoding='utf-8') as jf:
                jf.write(ssh_command)
                jf.write("\n")

        logger.info("initiate_download_study_dataset::end %s", study_name)
        thread = threading.Thread(target=check_file_and_send_email, args=(user_details, filename))
        thread.start()
        return True
    except Exception as exc:
        logger.info("An error occurred: %s", exc)
        return False


def create_local_test_study_dataset(study_name, data_type, filename, user_details):
    """Create a test-study dataset ZIP locally and register its email link."""
    study_root = os.path.realpath(os.path.join(config.studies_folder, study_name))
    studies_root = os.path.realpath(config.studies_folder)
    download_root = os.path.join(config.storage_folder, config.download_folder)
    zip_path = os.path.join(download_root, filename + constants.zip_extension)
    partial_zip_path = zip_path + ".part"

    try:
        if os.path.commonpath([studies_root, study_root]) != studies_root:
            raise ValueError("Study name resolves outside the local studies folder.")
        if not os.path.isdir(study_root):
            raise FileNotFoundError(f"Local study folder not found: {study_root}")

        os.makedirs(download_root, exist_ok=True)
        files_added = 0
        with zipfile.ZipFile(partial_zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            def add_tree(source_folder, archive_root):
                nonlocal files_added
                for root, directories, files in os.walk(source_folder):
                    directories[:] = [
                        directory
                        for directory in directories
                        if not os.path.islink(os.path.join(root, directory))
                    ]
                    if data_type == "raw":
                        directories[:] = [
                            directory
                            for directory in directories
                            if directory not in {"processed", "combined"}
                        ]
                    for file_name in files:
                        source_path = os.path.join(root, file_name)
                        if os.path.islink(source_path):
                            continue
                        relative_path = os.path.relpath(source_path, source_folder)
                        archive.write(
                            source_path,
                            os.path.join(archive_root, relative_path),
                        )
                        files_added += 1

            canonical_inputs = os.path.join(study_root, "inputs")
            canonical_metadata = os.path.join(study_root, "metadata")
            if os.path.isdir(canonical_inputs):
                add_tree(canonical_inputs, "inputs")
            if os.path.isdir(canonical_metadata):
                add_tree(canonical_metadata, "metadata")

            if not os.path.isdir(canonical_inputs):
                subject_prefix = study_name + "_"

                # Older test studies store subject-activation folders directly
                # below the study directory.
                for entry in sorted(os.scandir(study_root), key=lambda item: item.name):
                    if (
                        entry.is_dir(follow_symlinks=False)
                        and entry.name.startswith(subject_prefix)
                    ):
                        add_tree(entry.path, os.path.join("inputs", entry.name))

                # Some local ingestion setups use one shared studies/inputs
                # directory instead of studies/<study>/inputs.
                shared_inputs = os.path.join(studies_root, "inputs")
                if os.path.isdir(shared_inputs):
                    for entry in sorted(
                        os.scandir(shared_inputs), key=lambda item: item.name
                    ):
                        if (
                            entry.is_dir(follow_symlinks=False)
                            and entry.name.startswith(subject_prefix)
                        ):
                            add_tree(entry.path, os.path.join("inputs", entry.name))

            if not os.path.isdir(canonical_metadata):
                # Normalize legacy root-level study metadata to the same
                # metadata/... archive layout produced by the remote exporter.
                for entry in sorted(os.scandir(study_root), key=lambda item: item.name):
                    if (
                        entry.is_file(follow_symlinks=False)
                        and not entry.name.startswith(".")
                    ):
                        archive.write(entry.path, os.path.join("metadata", entry.name))
                        files_added += 1

        if files_added == 0:
            raise RuntimeError(f"No files found to archive under: {study_root}")
        with zipfile.ZipFile(partial_zip_path, "r") as archive:
            invalid_member = archive.testzip()
            if invalid_member:
                raise RuntimeError(
                    f"ZIP integrity check failed for member: {invalid_member}"
                )
        os.replace(partial_zip_path, zip_path)
        set_download_file_permissions(zip_path)
        logger.info("Created local test-study dataset ZIP: %s", zip_path)
        check_file_and_send_email(
            user_details,
            filename,
            send_link_email=True,
        )
    except Exception:
        logger.exception(
            "Local dataset generation failed for test study %s", study_name
        )
        if os.path.exists(partial_zip_path):
            try:
                os.remove(partial_zip_path)
            except OSError:
                logger.warning("Could not remove partial ZIP: %s", partial_zip_path)

def check_file_and_send_email(user_details, filename, send_link_email=False):
    """
    Register a dataset download and optionally email its link immediately.

    Normal remote-study downloads retain their existing token-registration
    behavior. Test-study ZIPs call this only after local generation succeeds
    and explicitly request immediate email delivery.
    """
    zip_filepath = os.path.join(
        config.storage_folder,
        config.download_folder,
        filename + constants.zip_extension,
    )
    token_instance = FileDownloadToken.objects.create(
        first_name=user_details.get("first_name"),
        email=user_details.get("email"),
        file_name=filename,
        status="initiated",
        expiration_date=timezone.now() + timedelta(days=7),
    )
    link = config.site_url + reverse("download_dataset", args=[token_instance.token])
    token_instance.link = link
    token_instance.save()

    if not send_link_email:
        return True

    if not os.path.isfile(zip_filepath):
        token_instance.status = "file missing"
        token_instance.save(update_fields=["status"])
        logger.error("Test-study dataset ZIP is missing: %s", zip_filepath)
        return False

    email_sent = send_email(
        "",
        user_details.get("email", ""),
        "",
        link,
    )
    status = "sent email" if email_sent else "email failed"
    token_instance.status = status
    token_instance.save(update_fields=["status"])
    return email_sent


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


def _log_subject_removal_audit(study_name, actor, subject_ids, dropout_reason, delete_data):
    try:
        StudyAuditService.log_subject_removal(
            study_name,
            actor,
            subject_ids,
            reason=dropout_reason,
            delete_data=delete_data,
        )
    except Exception:
        logger.exception(
            "Failed to write subject-removal audit entry for study=%s subject_ids=%s",
            study_name,
            subject_ids,
        )


def remove_subjects_from_study(
    study_name,
    subject_to_remove,
    context,
    actor=None,
    dropout_reason="",
):
    """
    Mark a selected subject as removed within the in-memory study detail context.
    """
    logger.info("remove_subjects_from_study:start")
    try:
        selected_subject_value = str(subject_to_remove)
        subject_id_with_modality = selected_subject_value.split(constants.value_sep, 1)[0]
        subject_id, app = subject_id_with_modality.split(constants.sep, 1)
        group_id = subject_id[:-2]
    except Exception as exc:
        logger.error("Failed to parse subject identifier '%s': %s", subject_to_remove, exc)
        return context

    group_subjects = context.get("d", {}).get(group_id)
    if group_subjects:
        for obj in group_subjects:
            if obj.get("subject_name") == subject_id and obj.get("app") == app:
                obj["status_code"] = constants.remove_status_code
                try:
                    Subject.remove_from_study(study_name, subject_id_with_modality)
                except Exception as exc:
                    logger.exception(
                        "Failed to update removed status in subject JSON for '%s': %s",
                        subject_id_with_modality,
                        exc,
                    )
                    context["error_message"] = controller_error_message(exc)
                    break
                _log_subject_removal_audit(
                    study_name,
                    actor,
                    subject_id_with_modality,
                    dropout_reason,
                    delete_data=False,
                )
                context["success_message"] = f"{subject_id} has been succesfully removed"
                break
    else:
        logger.warning("Group '%s' not found or is empty. Skipping status update.", group_id)

    try:
        context["subject_details"]["ids_to_be_removed"].remove(selected_subject_value)
    except ValueError:
        logger.warning("Subject '%s' not found in ids_to_be_removed.", selected_subject_value)

    logger.info("remove_subjects_from_study:end")
    if "success_message" not in context:
        context["success_message"] = f"{subject_id} not found but marked processed"
    return context


def mark_subject_as_left(study_name, subject_to_change, context):
    """Set selected subject modalities to Left while retaining their data."""
    selected_values = (
        subject_to_change
        if isinstance(subject_to_change, (list, tuple, set))
        else [subject_to_change]
    )
    updated_subject_ids = []
    for selected_value in selected_values:
        try:
            subject_with_modality = str(selected_value).split(constants.value_sep, 1)[0]
            subject_id, app = subject_with_modality.split(constants.sep, 1)
            Subject.mark_as_left(study_name, subject_with_modality)

            group_id = subject_id[:-2]
            for subject_row in context.get("d", {}).get(group_id, []):
                if subject_row.get("subject_name") == subject_id and subject_row.get("app") == app:
                    subject_row["status_code"] = constants.left_status_code
                    break
            updated_subject_ids.append(subject_id)
        except Exception as exc:
            logger.exception(
                "Failed to mark subject as left: study=%s subject=%s",
                study_name,
                selected_value,
            )
            context[constants.key_name_error_message] = controller_error_message(exc)

    if updated_subject_ids:
        context[constants.key_name_success_message] = (
            f"{len(updated_subject_ids)} subject activation(s) have been marked as left"
        )
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
        for test_case in context[constants.key_name_test_list]:
            comments = test_case.get("comments", [])
            notes_list = [
                {
                    "text": str(comment.get("text", "")).strip(),
                    "user": str(comment.get("user", "")).strip(),
                    "timestamp": str(comment.get("timestamp", "")).strip(),
                }
                for comment in comments
                if str(comment.get("text", "")).strip()
            ]
            test_case["notes_list"] = notes_list
            test_case["notes_preview"] = notes_list[-3:]
            test_case["notes_json"] = json.dumps(notes_list)
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


def delete_subjects_from_server(study_name, subject_ids, actor=None, dropout_reason=""):
    """
    Delete generated files for the selected subject ids from local storage.
    """
    from jdash.utils.fileutils import delete_user_files

    logger.info("delete_subjects_from_server subject  :start")
    deleted_subject_ids = []
    for subject_id in subject_ids.split(constants.value_sep):
        subject_id = subject_id.strip()
        if not subject_id:
            logger.info("Skipped empty subject_id")
            continue
        logger.info("delete_subjects_from_server subject_id %s", subject_id)
        delete_user_files(study_name, subject_id)
        deleted_subject_ids.append(subject_id)
    if deleted_subject_ids:
        _log_subject_removal_audit(
            study_name,
            actor,
            deleted_subject_ids,
            dropout_reason,
            delete_data=True,
        )
    logger.info("delete_subjects_from_server subject  :end")
