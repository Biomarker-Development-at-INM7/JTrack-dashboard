import json
import logging
from datetime import datetime
from django.utils import timezone
from auditlog.models import LogEntry
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.forms.formsets import formset_factory
from django.shortcuts import render, redirect
from django.http import JsonResponse
from jdash.services.subject import Subject

from jdash.audit.services import StudyAuditService
from jdash.services.controller import (
    close_study,
    create_display_sop_list_of_study,
    create_new_study,
    create_subjects_for_study,
    download_dataset,
    delete_subjects_from_server,
    remove_subjects_from_study,
    update_study_meta_data,
)
from jdash.services.notification import send_email, send_push_notification,send_qc_comment_email
from jdash.services.study import Study
from jdash.forms import (
    CreateStudyForm,
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
from jdash.utils.fileutils import get_json_data
from jdash.repositories.study_repository import update_test_case_flags,append_qc_note
from jdash.repositories.survey_repository import (
        retrieve_all_survey_for_user,
        retrieve_surveys_visible_to_study_editor,
        )
from jdash.models import FileDownloadToken, Study as studymodel,StudyDeviceSensor,QualityControlTests
from jdash.config.textmessages import TextMessages as textmessages

from django.http import HttpResponse

logger = logging.getLogger("django")


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
    context = Study(study_name, request.user).display_context()

    if constants.button_name_send_notification in request.POST:
        form = SendNotificationForm(
            request.POST,
            receivers=context[constants.key_name_subject_details][constants.key_name_ids_to_be_removed],
        )
        if form.is_valid():
            message_title, message_text, receivers = get_notification_form_data(form)
            send_push_notification(message_title, message_text, receivers, study_name)
    elif constants.button_name_create_subjects in request.POST:
        form = CreateSubjectForm(request.POST)
        if form.is_valid():
            result_context = create_subjects_for_study(
                study_name,
                form.cleaned_data.get(constants.field_name_number_of_subjects),
            )

            if constants.key_name_error_message in result_context:
                context.update(result_context)
            else:
                return redirect("details", study_name=study_name)
    elif constants.button_name_remove_subjects in request.POST:
        form = RemoveSubjectsForm(
            request.POST,
            receivers=context[constants.key_name_subject_details][constants.key_name_ids_to_be_removed],
        )
        if form.is_valid():
            context = remove_subjects_from_study(
                study_name,
                form.cleaned_data.get(constants.field_name_subject_to_remove),
                context,
            )
    elif constants.button_name_delete_subject_data in request.POST:
        selected_ids = request.POST[constants.field_name_subjectId]
        delete_subjects_from_server(study_name, selected_ids)
        LogEntry.objects.select_related('actor', 'content_type').order_by('-timestamp')[:200]

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
def close(request, study_name):
    """
    Closes the selected study and renders the result.

    Args:
        request (HttpRequest): The HTTP request object.
        study_name (str): The name of the study to be closed.

    Returns:
        HttpResponse: Home page or error page.
    """
    context = {}
    (
        context[constants.key_name_study_meta],
        context[constants.key_name_stats],
        context[constants.key_name_error_message],
    ) = close_study(study_name, request.user)
    if not context[constants.key_name_error_message]:
        study_meta = context[constants.key_name_study_meta]
        request.session[constants.session_key_studies] = study_meta
        request.session[constants.session_key_studies_stats] = context[constants.key_name_stats]
        request.session[constants.session_key_studies_ema] = list({
            study[constants.key_name_study_title]
            for study in study_meta
            if constants.ema in (study.get(constants.key_name_sensor_list) or [])
        })
        request.session[constants.session_key_old_ema] = [
            study[constants.key_name_study_title]
            for study in study_meta
            if "old_ema" in study
        ]
        request.session[constants.session_key_survey_details] = None
        request.session.modified = True
        return render(request, constants.home_page, context=context)
    return render(request, constants.error_page, context=context)


def download_dataset_from_link(request, arg):
    """
    Handles dataset download requests triggered through a tokenized email link.

    This view validates the token, optionally checks the confirmation code,
    marks the token as downloaded, and streams the requested dataset.

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
        logger.warning("Invalid or expired download token: %s", arg)
        return render(request, constants.error_page, context={})

    if constants.button_name_download_data_confirm in request.GET:
        logger.info("Download confirmation requested for token: %s", arg)
        verify_code = request.GET.get('verifyCode', '')
        if download_token.code != verify_code:
            messages.error(request, "Invalid verification code.")
            return render(request, constants.download_confirm, context={'arg': arg})

        study_name = download_token.file_name
        logger.info("download_dataset_from_link::download request for %s data", study_name)
        download_token.status = "downloaded"
        download_token.downloaded = timezone.now()
        download_token.save()
        return download_dataset(study_name)

    logger.info("Sending confirmation email for download token: %s", arg)
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
            logger.warning("BEFORE create_new_study")

            try:
                with transaction.atomic():
                    context = create_new_study(
                        form,
                        task_formset,
                        request,
                        study_device_formset,
                        sensor_formsets,
                    )

                logger.warning("AFTER create_new_study context=%s", context)

            except Exception as e:
                logger.exception("create_new_study failed")
                return HttpResponse(f"ERROR: {e}")

            logger.warning(
                "USER AUTH AFTER CREATE: %s",
                request.user.is_authenticated
            )

            if not context.get(constants.key_name_error_message):
                messages.success(request, context[constants.key_name_success_message])

                request.session.pop(constants.session_key_studies, None)
                request.session.pop(constants.session_key_studies_stats, None)
                request.session.pop(constants.session_key_studies_ema, None)
                request.session.pop(constants.session_key_old_ema, None)
                request.session.modified = True
                messages.success(request, "Study created")

                return redirect(constants.url_name_for_home)

        #if all_valid:
        #    with transaction.atomic():
        #        context = create_new_study(
        #            form,
        #            task_formset,
        #            request,
        #            study_device_formset,
        #            sensor_formsets,
        #        )

        #    request.session[constants.session_key_studies] = None
        #    request.session[constants.session_key_studies_stats] = None
        #    request.session[constants.session_key_studies_ema] = []

        #    if not context.get(constants.key_name_error_message):
        #        messages.success(request, context[constants.key_name_success_message])
        #        return render(request, constants.home_page, context=context)

        #    error = context.get(constants.key_name_error_message, "")

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
    messages.error(request, error)
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
    context = {}
    error = context.get(constants.key_name_error_message, "")
    json_meta = get_json_data(study_name)

    try:
        study = studymodel.objects.get(title=study_name)
    except studymodel.DoesNotExist:
        messages.error(request, "Study not found.")
        return render(request, constants.home_page, context=context)

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

                #if study_name == "Test":
                #    json_meta = get_json_data(study_name)
                #    number_of_subjects = json_meta.get("number_of_subjects") or json_meta.get("number-of-subjects") or 350
                #    Subject.create_pdfs_for_study(study_name, int(number_of_subjects))

                context[constants.key_name_survey_form] = SurveyForm()
                context[constants.key_name_question_form] = QuestionForm()
                messages.success(request, textmessages.success_study_updated)
                request.session[constants.session_key_survey_details] = None
                return render(request, constants.home_page, context=context)
            logger.warning("edit_study:: validation failed for study_name=%s", study_name)
            logger.warning("Study form errors: %s", form.errors)
            logger.warning("Task formset errors: %s", formset.errors)
            logger.warning("Device formset errors: %s", study_device_formset.errors)
            for i, sf in enumerate(sensor_formsets):
                logger.warning("Sensor formset %s errors: %s", i, sf.errors)

    if json_meta.get("survey"):
        survey = normalize_survey_data(json_meta)

        if not survey.get("id"):
            context["is_file"] = True
            context[constants.key_name_study_form] = CreateStudyForm(
                json_data=json_meta,
                survey=survey_list_obj,
            )
        else:
            logger.debug("json in the attached study file %s", json_meta)
            context["is_file"] = False
            context[constants.key_name_study_form] = CreateStudyForm(
                json_data=json_meta,
                survey=survey_list_obj,
                initial_survey_id=survey.get("id", ""),
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

    messages.error(request, error)
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
                update_test_case_flags(testcase_updates, username)
        else:
            logger.warning(
                "qc_study received empty test_case_flags for study=%s user=%s",
                study_name,
                request.user.username,
            )
    context = create_display_sop_list_of_study(study_name)
    context["qc_username"] = request.user.username
    return render(request, constants.sop_list_of_study_page, context)

@login_required
def notify_qc_comment(request, study_name):
    """Send an email notification when a QC comment is added from the modal."""
    if request.method != constants.post_method:
        return JsonResponse({"ok": False, "error": "Method not allowed"}, status=405)

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
    study = studymodel.objects.get(title=study_name)
    context = {
        "study": study,
        "audit_history": StudyAuditService.get_history(study),
    }
    return render(request, constants.study_audit_page, context)
