import json
import logging
import os
import re
from datetime import datetime

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms.formsets import formset_factory
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from jdash.audit.services import StudyAuditService
from jdash.services.controller import (
    close_study,
    create_display_sop_list_of_study,
    create_new_study,
    create_subjects_for_study,
    download_dataset,
    download_study_dashboard_csv,
    download_combined_study_dashboard_csv,
    download_study_wearables_csv,
    mark_subject_as_left,
    delete_subjects_from_server,
    remove_subjects_from_study,
    update_study_meta_data,
)
from jdash.services.notification import send_email, send_push_notification, send_qc_comment_email
from jdash.services import permissions
from jdash.services.study import Study
from jdash.forms import (
    CreateStudyForm,
    ChangeSubjectStatusForm,
    CreateSubjectForm,
    QuestionForm,
    RemoveSubjectsForm,
    SendNotificationForm,
    SurveyForm,
    TaskForm,
    StudyDeviceFormSet,
    StudyDeviceSensorFormSet,
)
from jdash.config import constants as constants
from jdash.config import runtime_config as config
from jdash.services.context_builder import (
    context_for_add_edit_study_page,
    context_for_home_page,
    context_for_study_detail_page,
)
from jdash.services.datahelper import (
    build_sensor_formsets,
    get_info_texts,
    get_notification_form_data,
    normalize_survey_data,
)
from jdash.utils.fileutils import (
    get_study_json_version_diff,
    get_json_data,
    list_study_json_versions,
    resolve_study_json_version_path,
)
from jdash.repositories.study_repository import append_qc_note, update_test_case_flags
from jdash.repositories.survey_repository import (
    retrieve_all_survey_for_user,
    retrieve_surveys_visible_to_study_editor,
)
from jdash.models import FileDownloadToken, Study as studymodel, StudyDeviceSensor, QualityControlTests
from jdash.config.textmessages import TextMessages as textmessages
from jdash.services.csv_refresh import request_study_csv_refresh
from jdash.views.message_helpers import (
    add_context_messages,
    add_form_error,
    forbidden_with_message,
)

logger = logging.getLogger("django")


def _forbidden(request, message="You do not have permission to perform this action."):
    return forbidden_with_message(request, message)


def _study_history_context(study, show_json_versions=False):
    try:
        json_versions = list_study_json_versions(study.title)
    except ValueError as exc:
        raise Http404("Study JSON versions not found.") from exc
    return {
        "study": study,
        "audit_history": StudyAuditService.get_history(study),
        "json_versions": json_versions,
        "show_json_versions": show_json_versions,
    }


@login_required
def study_title_availability(request):
    """Return whether a proposed study title is already in use."""
    if not permissions.can_create_study(request.user):
        return JsonResponse({"available": False, "reason": "forbidden"}, status=403)

    title = request.GET.get("title", "").strip()
    if not title or not re.fullmatch(r"[A-Za-z0-9_]+", title):
        return JsonResponse({"available": False, "reason": "invalid"}, status=400)

    database_exists = studymodel.objects.filter(title__iexact=title).exists()
    folder_paths = (
        os.path.join(config.studies_folder, title),
        os.path.join(settings.DASH_FOLDER, config.app_study_folder, title),
    )
    folder_exists = any(os.path.isdir(path) for path in folder_paths)

    return JsonResponse({
        "available": not database_exists and not folder_exists,
        "database_exists": database_exists,
        "folder_exists": folder_exists,
    })


@login_required
def study_details(request, study_name):
    """
    Renders the study details page and processes study-level actions.

    This view handles notifications, subject creation, subject removal, and
    subject-data deletion requests from the study details page.

    Args:
        request (HttpRequest): The HTTP request object.
        study_name (str): Study name being viewed.

    Returns:
        HttpResponse: Rendered study details or home page on error.
    """
    study_record = studymodel.objects.filter(title=study_name).first()
    if study_record is None or not permissions.can_view_study(request.user, study_record):
        return _forbidden(request)

    if request.method == "GET":
        try:
            csv_ready = request_study_csv_refresh(study_name)

            if not csv_ready:
                logger.info(
                    "Dashboard CSV refresh requested in the background for study=%s",
                    study_name,
                )
        except (FileNotFoundError, TimeoutError, RuntimeError, OSError):
            logger.exception(
                "Could not refresh dashboard CSV for study %s",
                study_name,
            )
            messages.warning(
                request,
                "The study data could not be refreshed. "
                "The latest available data will be displayed."
            )
    context = Study(study_name, request.user).display_context()
    context["can_conclude_study"] = permissions.can_conclude_study(
        request.user,
        study_record,
    )

    study_management_posts = {
        constants.button_name_send_notification,
        constants.button_name_create_subjects,
        constants.button_name_remove_subjects,
        constants.button_name_change_subject_status,
        constants.button_name_delete_subject_data,
    }
    if request.method == constants.post_method and any(name in request.POST for name in study_management_posts):
        if not permissions.can_manage_study(request.user, study_record):
            return _forbidden(request)

    study_management_posts = {
        constants.button_name_send_notification,
        constants.button_name_create_subjects,
        constants.button_name_remove_subjects,
        constants.button_name_change_subject_status,
        constants.button_name_delete_subject_data,
    }
    if request.method == constants.post_method and any(name in request.POST for name in study_management_posts):
        if not permissions.can_manage_study(request.user):
            return _forbidden()

    if constants.button_name_send_notification in request.POST:
        form = SendNotificationForm(
            request.POST,
            receivers=context[constants.key_name_subject_details][constants.key_name_ids_to_be_removed],
        )
        if form.is_valid():
            message_title, message_text, receivers = get_notification_form_data(form)
            _, notification_delivery_results = send_push_notification(
                message_title,
                message_text,
                receivers,
                study_name,
                include_results=True,
            )
            context["notification_delivery_results"] = notification_delivery_results
            context["sent_notification_title"] = message_title
            context["sent_notification_text"] = message_text
            logger.info(
                "User action=send_notification user=%s study=%s receiver_count=%s",
                request.user.get_username(),
                study_name,
                len(receivers),
            )
        else:
            add_form_error(request, "send the notification")
    elif constants.button_name_create_subjects in request.POST:
        form = CreateSubjectForm(request.POST)
        if form.is_valid():
            creation_context = create_subjects_for_study(
                study_name,
                form.cleaned_data.get(constants.field_name_number_of_subjects),
            )
            if isinstance(creation_context, dict):
                error_message = creation_context.get(constants.key_name_error_message)
                if error_message:
                    messages.error(request, error_message)
                    return redirect(constants.url_name_for_details, study_name=study_name)
                else:
                    success_message = creation_context.get(
                        constants.key_name_success_message,
                        "Subjects were added successfully.",
                    )
                    logger.info(
                        "User action=create_subjects user=%s study=%s count=%s",
                        request.user.get_username(),
                        study_name,
                        form.cleaned_data.get(constants.field_name_number_of_subjects),
                    )
                    messages.success(request, success_message)
                    return redirect(constants.url_name_for_details, study_name=study_name)
            else:
                messages.success(request, "Subjects were added successfully.")
                return redirect(constants.url_name_for_details, study_name=study_name)
        else:
            add_form_error(request, "create subjects")
    elif constants.button_name_remove_subjects in request.POST:
        dropout_reason = request.POST.get(constants.field_name_dropout_reason, "")
        form = RemoveSubjectsForm(
            request.POST,
            receivers=context[constants.key_name_subject_details][constants.key_name_ids_to_be_removed],
        )
        if form.is_valid():
            removal_context = remove_subjects_from_study(
                study_name,
                form.cleaned_data.get(constants.field_name_subject_to_remove),
                context,
                actor=request.user,
                dropout_reason=dropout_reason,
            )
            removal_error = removal_context.get(constants.key_name_error_message)
            removal_success = removal_context.get(constants.key_name_success_message)
            if removal_error:
                messages.error(request, removal_error)
            if removal_success:
                logger.info(
                    "User action=remove_subject user=%s study=%s subject=%s",
                    request.user.get_username(),
                    study_name,
                    form.cleaned_data.get(constants.field_name_subject_to_remove),
                )
                messages.success(request, removal_success)
            if not removal_error and not removal_success:
                messages.warning(request, "No subject was removed.")
            return redirect(constants.url_name_for_details, study_name=study_name)
        else:
            add_form_error(request, "remove the subject")
    elif constants.button_name_change_subject_status in request.POST:
        form = ChangeSubjectStatusForm(
            request.POST,
            subjects=context[constants.key_name_subject_details][constants.key_name_ids_to_be_removed],
        )
        if form.is_valid():
            context = mark_subject_as_left(
                study_name,
                form.cleaned_data["subject_to_change"],
                context,
            )
            status_error = context.get(constants.key_name_error_message)
            status_success = context.get(constants.key_name_success_message)
            if status_error:
                messages.error(request, status_error)
            if status_success:
                logger.info(
                    "User action=change_subject_status user=%s study=%s subject=%s",
                    request.user.get_username(),
                    study_name,
                    form.cleaned_data.get("subject_to_change"),
                )
                messages.success(request, status_success)
            if status_error or status_success:
                return redirect(constants.url_name_for_details, study_name=study_name)
            messages.warning(request, "No subject status was changed.")
        else:
            add_form_error(request, "change the subject status")
    elif constants.button_name_delete_subject_data in request.POST:
        try:
            selected_ids = request.POST.get(constants.field_name_subjectId, "").strip()
            if not selected_ids:
                raise ValueError("No subject was selected.")
            delete_subjects_from_server(
                study_name,
                selected_ids,
                actor=request.user,
                dropout_reason=request.POST.get(constants.field_name_dropout_reason, ""),
            )
            logger.info(
                "User action=delete_subject_data user=%s study=%s subject_count=%s",
                request.user.get_username(),
                study_name,
                len([value for value in selected_ids.split(constants.value_sep) if value.strip()]),
            )
            messages.success(request, "The selected subject data was deleted successfully.")
        except Exception as exc:
            logger.exception("Could not delete subject data for study=%s", study_name)
            messages.error(
                request,
                str(exc) if isinstance(exc, ValueError) else "The selected subject data could not be deleted.",
            )
        return redirect(constants.url_name_for_details, study_name=study_name)

    if constants.key_name_error_message in context:
        context.update(context_for_home_page(request.user))
        messages.error(request, context[constants.key_name_error_message])
        return render(request, constants.home_page, context)

    context.update(
        context_for_study_detail_page(
            study_name,
            request.session.session_key,
            subject_details=context.get(constants.key_name_subject_details),
        )
    )
    return render(request, constants.details_page, context)


@login_required
def export_study_dashboard_csv(request, study_name):
    """Download the generated dashboard CSV for a study."""
    study = studymodel.objects.filter(title=study_name).first()
    if study is None or not permissions.can_view_study(request.user, study):
        return _forbidden(request, "You do not have permission to export this study.")
    return download_study_dashboard_csv(study_name)


@login_required
def export_study_wearables_csv(request, study_name):
    """Download the wearable CSV used by the study details table."""
    study = studymodel.objects.filter(title=study_name).first()
    if study is None or not permissions.can_view_study(request.user, study):
        return _forbidden(request, "You do not have permission to export this study.")
    return download_study_wearables_csv(study_name)


@login_required
def export_combined_study_dashboard_csv(request, study_name):
    """Download the main and wearable dashboard data as one CSV."""
    study = studymodel.objects.filter(title=study_name).first()
    if study is None or not permissions.can_view_study(request.user, study):
        return _forbidden(request, "You do not have permission to export this study.")
    return download_combined_study_dashboard_csv(study_name)


@login_required
@require_POST
def close(request, study_name):
    """
    Closes the selected study and renders the result.

    Args:
        request (HttpRequest): The HTTP request object.
        study_name (str): The name of the study to be closed.

    Returns:
        HttpResponse: Home page or error page.
    """
    study_record = studymodel.objects.filter(title=study_name, closed=False).first()
    if study_record is None or not permissions.can_conclude_study(request.user, study_record):
        return _forbidden(request)

    context = {}
    (
        context[constants.key_name_study_meta],
        context[constants.key_name_stats],
        context[constants.key_name_error_message],
    ) = close_study(study_name, request.user)
    if not context[constants.key_name_error_message]:
        messages.success(request, f"{study_name} was closed successfully.")
        return render(request, constants.home_page, context=context)
    messages.error(request, context[constants.key_name_error_message])
    return render(request, constants.error_page, context=context)


def download_dataset_from_link(request, arg):
    """
    Handles dataset download requests triggered through a tokenized email link.

    This view validates the token, optionally checks the confirmation code,
    deletes the one-time token, and streams the requested dataset.

    Args:
        request (HttpRequest): The HTTP request object.
        arg (str): Token identifying the download request.

    Returns:
        HttpResponse: Confirmation page, error page, or dataset response.
    """
    try:
        download_token = FileDownloadToken.objects.get(
            token=arg,
            expiration_date__gte=timezone.now(),
        )
    except FileDownloadToken.DoesNotExist:
        logger.warning("Invalid or expired download token prefix=%s", str(arg)[:8])
        messages.error(request, "This download link is invalid or has expired.")
        return render(request, constants.error_page, context={})

    if download_token.status == "invalidated":
        logger.info("Download token invalidated after study data changed")
        messages.warning(request, "This download is no longer available because the study data changed.")
        return render(
            request,
            constants.download_confirm,
            context={"arg": arg, "download_invalidated": True},
        )

    if download_token.status == "downloaded":
        logger.info("Download token has already been used")
        messages.info(request, "This download link has already been used.")
        return render(
            request,
            constants.download_confirm,
            context={"arg": arg, "download_complete": True},
        )

    if constants.button_name_download_data_confirm in request.GET:
        logger.info("Download confirmation requested")
        verify_code = request.GET.get('verifyCode', '')
        if download_token.code != verify_code:
            messages.error(request, "Invalid verification code.")
            return render(request, constants.download_confirm, context={'arg': arg})

        study_name = download_token.file_name
        logger.info("download_dataset_from_link::download request for %s data", study_name)
        response = download_dataset(study_name)
        download_token.delete()
        return response

    logger.info("Sending confirmation email for dataset download")
    send_email("", download_token.email, arg, "confirm")
    return render(request, constants.download_confirm, context={'arg': arg})


@login_required
def add_study(request):
    """
    Handles creation of a new study.

    This view validates the study form, task formset, device formset, and
    related sensor formsets, then delegates creation to the study workflow.

    Returns:
        HttpResponse: Create page, home page, or error page.
    """
    if not permissions.can_create_study(request.user):
        return _forbidden(request)

    context = {}
    error = ""
    survey_list_obj = retrieve_all_survey_for_user(request.user, request.session.session_key)
    TaskFormSet = formset_factory(TaskForm)

    form = CreateStudyForm(request.POST or None, request.FILES or None, survey=survey_list_obj)
    task_formset = TaskFormSet(request.POST or None)
    study_device_formset = StudyDeviceFormSet(request.POST or None, prefix="devices")
    sensor_formsets = []

    if request.method == constants.post_method:
        logger.debug("add_study:: new study creation started %s", request.POST)
        devices_valid = study_device_formset.is_valid()

        if devices_valid:
            for i in range(study_device_formset.total_form_count()):
                sf_prefix = f"sensors-{i}"
                dform = study_device_formset.forms[i]

                if (not dform.cleaned_data) or dform.cleaned_data.get("DELETE") or not dform.cleaned_data.get("device"):
                    sf = StudyDeviceSensorFormSet(
                        request.POST,
                        prefix=sf_prefix,
                        queryset=StudyDeviceSensor.objects.none(),
                        device=None,
                    )
                    sensor_formsets.append(sf)
                    continue

                device_obj = dform.cleaned_data["device"]
                sf = StudyDeviceSensorFormSet(
                    request.POST,
                    prefix=sf_prefix,
                    queryset=StudyDeviceSensor.objects.none(),
                    device=device_obj,
                )
                sensor_formsets.append(sf)

            sensors_valid = all(sf.is_valid() for sf in sensor_formsets)
        else:
            sensors_valid = False

        all_valid = form.is_valid() and task_formset.is_valid() and devices_valid and sensors_valid

        if all_valid:
            with transaction.atomic():
                context = create_new_study(
                    form,
                    task_formset,
                    request,
                    study_device_formset,
                    sensor_formsets,
                )

            request.session[constants.session_key_studies] = None

            if not context.get(constants.key_name_error_message):
                messages.success(request, context[constants.key_name_success_message])
                return render(request, constants.home_page, context=context)

            error = context.get(constants.key_name_error_message, "")

        else:
            logger.warning("add_study:: validation failed")
            logger.warning("Study form errors: %s", form.errors)
            logger.warning("Task formset errors: %s", task_formset.errors)
            logger.warning("Device formset errors: %s", study_device_formset.errors)
            for i, sf in enumerate(sensor_formsets):
                logger.warning("Sensor formset %s errors: %s", i, sf.errors)

    else:
        for i in range(study_device_formset.total_form_count()):
            sf_prefix = f"sensors-{i}"
            sf = StudyDeviceSensorFormSet(
                prefix=sf_prefix,
                queryset=StudyDeviceSensor.objects.none(),
                device=None,
            )
            sensor_formsets.append(sf)

    context = context_for_home_page(request.user)
    context.update(
        context_for_add_edit_study_page(
            "",
            form,
            task_formset,
            study_device_formset,
            sensor_formsets,
            "",
        )
    )

    context[constants.key_name_info_text] = get_info_texts()
    if error:
        messages.error(request, error)
    elif request.method == constants.post_method:
        add_form_error(request, "create the study")
    return render(request, constants.create_study_page, context)


@login_required
def edit_study(request, study_name):
    """
    Handles editing of an existing study.

    This view loads current study metadata, prepopulates the study, task,
    device, and sensor formsets, and delegates the update workflow.

    Args:
        request (HttpRequest): The HTTP request object.
        study_name (str): The name of the study to edit.

    Returns:
        HttpResponse: Rendered study edit page or home page on success.
    """
    if not permissions.can_manage_study(request.user):
        return _forbidden()

    context = {}
    try:
        study = studymodel.objects.get(title=study_name)
    except studymodel.DoesNotExist:
        messages.error(request, "Study not found.")
        return render(request, constants.home_page, context=context)
    except studymodel.MultipleObjectsReturned:
        duplicate_ids = list(
            studymodel.objects.filter(title=study_name)
            .order_by("id")
            .values_list("id", flat=True)
        )
        logger.error(
            "Cannot edit study %s because duplicate rows exist: ids=%s",
            study_name,
            duplicate_ids,
        )
        messages.error(
            request,
            "This study has duplicate database records and cannot be edited safely. "
            "Please remove the duplicates and try again.",
        )
        context.update(context_for_home_page(request.user))
        return render(request, constants.home_page, context=context)

    if not permissions.can_manage_study(request.user, study):
        return _forbidden(request)

    json_meta = get_json_data(study_name)

    survey_data = json_meta.get("survey")
    if survey_data and not isinstance(survey_data, dict):
        try:
            survey_data = json.loads(survey_data) if isinstance(survey_data, str) else {}
        except json.JSONDecodeError:
            logger.warning("edit_study:: survey metadata is not valid JSON for %s", study_name)
            survey_data = {}
    json_meta["survey"] = survey_data or {}

    current_survey_id = study.survey_id
    if survey_data and survey_data.get("id"):
        current_survey_id = survey_data["id"]
    survey_list_obj = retrieve_surveys_visible_to_study_editor(
        request.user,
        survey_id=current_survey_id,
    )

    TaskFormSet = formset_factory(TaskForm, extra=1)
    form = CreateStudyForm(request.POST, survey=survey_list_obj)
    if request.method == constants.post_method:
        sensor_formsets = []
        formset = TaskFormSet(request.POST)
        study_device_formset = StudyDeviceFormSet(request.POST, prefix="devices")
        form = CreateStudyForm(request.POST, survey=survey_list_obj)
        tasks_valid = formset.is_valid()
        devices_valid = study_device_formset.is_valid()
        sensor_formsets = build_sensor_formsets(
            request.POST,
            study=study,
            device_forms=study_device_formset.forms,
        )
        sensors_valid = devices_valid and all(sf.is_valid() for sf in sensor_formsets)
        if constants.button_name_update_study in request.POST:
            all_valid = form.is_valid() and tasks_valid and devices_valid and sensors_valid
            if all_valid:
                context = update_study_meta_data(
                    study_name,
                    form,
                    formset,
                    request,
                    study_device_formset,
                    sensor_formsets,
                )
                context[constants.key_name_survey_form] = SurveyForm()
                context[constants.key_name_question_form] = QuestionForm()
                update_error = context.get(constants.key_name_error_message)
                if update_error:
                    messages.error(request, update_error)
                else:
                    messages.success(request, textmessages.success_study_updated)
                request.session[constants.session_key_survey_details] = None
                return render(request, constants.home_page, context=context)
            logger.warning("edit_study:: validation failed for study_name=%s", study_name)
            logger.warning("Study form errors: %s", form.errors)
            logger.warning("Task formset errors: %s", formset.errors)
            logger.warning("Device formset errors: %s", study_device_formset.errors)
            for i, sf in enumerate(sensor_formsets):
                logger.warning("Sensor formset %s errors: %s", i, sf.errors)
            add_form_error(request, "update the study")

    if survey_data:
        if  survey_data not in (None, {}) and not survey_data.get("id"):
            context["is_file"] = True
            context[constants.key_name_study_form] = CreateStudyForm(json_data=json_meta, survey=survey_list_obj)
        else:
            logger.debug("json in the attached study file %s", json_meta)
            context["is_file"] = False
            context[constants.key_name_study_form] = CreateStudyForm(
                json_data=json_meta,
                survey=survey_list_obj,
                initial_survey_id=survey_data["id"],
            )
    else:
        context[constants.key_name_study_form] = CreateStudyForm(
            json_data=json_meta,
            survey=survey_list_obj,
        )

    task_formset = TaskFormSet(initial=json_meta.get(constants.key_name_task_list, []))

    initial_devices = list(
        StudyDeviceSensor.objects.filter(study=study)
        .values_list("device_sensor__device_id", flat=True)
        .distinct()
    )
    study_device_formset = StudyDeviceFormSet(
        prefix="devices",
        initial=[{"device": did} for did in initial_devices],
    )
    sensor_formsets = build_sensor_formsets(
        None,
        study=study,
        device_forms=study_device_formset.forms,
    )

    context.update(
        context_for_add_edit_study_page(
            study_name,
            form,
            task_formset,
            study_device_formset,
            sensor_formsets,
            json_meta,
        )
    )

    logger.debug("edit_study:: context study name %s", context)
    return render(request, constants.edit_study_page, context=context)


@login_required
def qc_study(request, study_name):
    """
    Handles the quality-control page for a specific study.

    Args:
        request (HttpRequest): The HTTP request object.
        study_name (str): Study being checked.

    Returns:
        HttpResponse: Rendered QC/SOP page.
    """
    study_record = studymodel.objects.filter(title=study_name, closed=False).first()
    if study_record is None or not permissions.can_qc_study(request.user, study_record):
        return _forbidden(request)

    if constants.button_name_update_test_flags in request.POST:
        test_flags_list = request.POST.get(constants.field_name_test_case_flags, "").strip()
        if test_flags_list:
            try:
                testcase_updates = json.loads(test_flags_list)
            except json.JSONDecodeError:
                logger.warning(
                    "qc_study received invalid test_case_flags for study=%s user=%s payload=%r",
                    study_name,
                    request.user.username,
                    test_flags_list[:200],
                )
                messages.error(request, "Unable to save QC updates. Please try again.")
            else:
                user_details = request.session.get(constants.session_key_user_details, {})
                username = user_details.get(constants.field_name_username, request.user.username)
                update_result = update_test_case_flags(
                    testcase_updates,
                    username,
                    study_record.id,
                    can_update_admin_checks=permissions.can_update_qc_admin_checks(
                        request.user,
                        study_record,
                    ),
                    can_update_owner_checks=permissions.can_update_qc_owner_checks(
                        request.user,
                        study_record,
                    ),
                )
                if update_result["failure_count"]:
                    messages.warning(
                        request,
                        "Some quality-control updates could not be saved."
                    )
                else:
                    logger.info(
                        "User action=update_qc user=%s study=%s update_count=%s",
                        request.user.get_username(),
                        study_name,
                        update_result.get("success_count", len(testcase_updates)),
                    )
                    messages.success(request, "Quality-control updates were saved successfully.")
        else:
            logger.warning(
                "qc_study received empty test_case_flags for study=%s user=%s",
                study_name,
                request.user.username,
            )
            messages.warning(request, "No quality-control changes were submitted.")
    context = create_display_sop_list_of_study(study_name)
    add_context_messages(request, context)
    context["qc_username"] = request.user.username
    context["can_update_qc_admin_checks"] = permissions.can_update_qc_admin_checks(
        request.user,
        study_record,
    )
    context["can_update_qc_owner_checks"] = permissions.can_update_qc_owner_checks(
        request.user,
        study_record,
    )
    context["can_update_qc_checks"] = (
        context["can_update_qc_admin_checks"]
        or context["can_update_qc_owner_checks"]
    )
    return render(request, constants.sop_list_of_study_page, context)


@login_required
def notify_qc_comment(request, study_name):
    """Send an email notification when a QC comment is added from the modal."""
    if request.method != constants.post_method:
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

    study = studymodel.objects.filter(title=study_name, closed=False).first()
    if study is None or not permissions.can_qc_study(request.user, study):
        return JsonResponse(
            {"ok": False, "error": "You do not have permission to add QC comments."},
            status=403,
        )

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"ok": False, "error": "Invalid payload"}, status=400)

    testcase_db_id = payload.get("id")
    comment_text = str(payload.get("comment", "")).strip()
    timestamp = str(payload.get("timestamp", "")).strip()
    username = request.user.username

    if not testcase_db_id or not comment_text:
        return JsonResponse({"ok": False, "error": "Missing comment data"}, status=400)

    test_case = QualityControlTests.objects.filter(
        id=testcase_db_id,
        study__title=study_name,
    ).values("testcase_id", "description").first()

    if not test_case:
        return JsonResponse({"ok": False, "error": "Test case not found"}, status=404)

    append_qc_note(
        testcase_db_id,
        {
            "text": comment_text,
            "user": username,
            "timestamp": timestamp,
        },
        username,
    )

    sent = send_qc_comment_email(
        study_name=study_name,
        testcase_id=test_case["testcase_id"],
        description=test_case["description"],
        comment_text=comment_text,
        username=username,
        timestamp=timestamp,
    )
    logger.info(
        "User action=add_qc_comment user=%s study=%s testcase=%s email_sent=%s",
        request.user.get_username(),
        study_name,
        test_case["testcase_id"],
        sent,
    )
    status_code = 200 if sent else 500
    return JsonResponse({"ok": sent, "saved": True}, status=status_code)



@login_required
def study_audit(request, study_name):
    """
    Renders the audit history page for a study.

    Args:
        request (HttpRequest): The HTTP request object.
        study_name (str): Study whose audit history is displayed.

    Returns:
        HttpResponse: Rendered study audit history page.
    """
    study = studymodel.objects.filter(title=study_name).first()
    if study is None or not permissions.can_view_study(request.user, study):
        return _forbidden(request, "You do not have permission to view this study's audit history.")
    context = _study_history_context(
        study,
        show_json_versions=request.GET.get("tab", "json-versions") != "audit-history",
    )
    return render(request, constants.study_audit_page, context)


@login_required
def study_json_versions(request, study_name):
    """Display the current study JSON and its versioned backup snapshots."""
    study = studymodel.objects.filter(title=study_name).first()
    if study is None or not permissions.can_view_study(request.user, study):
        return _forbidden(request, "You do not have permission to view this study's JSON versions.")
    context = _study_history_context(study, show_json_versions=True)
    return render(request, constants.study_audit_page, context)


@login_required
def study_json_version_diff(request, study_name, version_key):
    """Return the field-level changes from the preceding study JSON version."""
    study = studymodel.objects.filter(title=study_name).first()
    if study is None or not permissions.can_view_study(request.user, study):
        return _forbidden(request, "You do not have permission to view this study's JSON versions.")
    try:
        comparison = get_study_json_version_diff(study.title, version_key)
    except (FileNotFoundError, ValueError, OSError, json.JSONDecodeError) as exc:
        raise Http404("Study JSON version not found.") from exc

    logger.info(
        "User action=view_study_json_version_diff user=%s study=%s version=%s change_count=%s",
        request.user.get_username(),
        study.title,
        version_key,
        len(comparison["changes"]),
    )
    return JsonResponse(comparison)


@login_required
def download_study_json_version(request, study_name, version_key):
    """Download one authorized current or archived study JSON snapshot."""
    study = studymodel.objects.filter(title=study_name).first()
    if study is None or not permissions.can_view_study(request.user, study):
        return _forbidden(request, "You do not have permission to download this study's JSON versions.")
    try:
        version_path = resolve_study_json_version_path(study.title, version_key)
    except (FileNotFoundError, ValueError) as exc:
        raise Http404("Study JSON version not found.") from exc

    logger.info(
        "User action=download_study_json_version user=%s study=%s version=%s",
        request.user.get_username(),
        study.title,
        version_key,
    )
    return FileResponse(
        open(version_path, "rb"),
        as_attachment=True,
        filename=os.path.basename(version_path),
        content_type="application/json",
    )
