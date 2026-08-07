import json
import logging
import os
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.forms.formsets import formset_factory
from django.http import HttpResponseForbidden
from django.http.response import HttpResponse
from django.shortcuts import render
from django.utils.translation import gettext as _
from jdash.audit.services import SurveyAuditService
from jdash.services import permissions
from jdash.services.controller import (
    create_question_answer_for_survey,
    create_survey_from_surveyForm,
    delete_question_from_file,
    delete_questions_from_file,
    delete_questions_from_survey,
    delete_survey_from_file,
    duplicate_and_create_new_question_id,
    duplicate_and_create_new_survey_id,
    duplicate_question_in_file,
    get_all_survey_details,
    update_categories_in_file,
    update_old_survey_details,
    update_question_answer_for_survey,
    update_question_order_in_file,
    update_survey_from_surveyForm,
    upload_survey_file,
)
from jdash.services.survey import Survey as SurveyService
from jdash.forms import AnswerForm, CategoryForm, JSONUploadForm, QuestionForm, SurveyForm
from jdash.config import constants as constants
from jdash.config import runtime_config as config
from jdash.services.context_builder import (
    context_for_create_survey_page,
    context_for_question_page,
    context_for_survey_list_page,
)
from jdash.services.datahelper import (
    get_category_form_data,
    get_help_texts_for_category_form,
    get_help_texts_for_question_form,
    get_question_form_data,
    get_survey_form_data,
)
from jdash.repositories.survey_repository import (
        delete_survey_for_user,
        retrieve_all_questions_for_survey,
        retrieve_all_categories_for_survey
)
from jdash.utils.fileutils import get_json_data
from jdash.interface.session_manager import SessionManager
from jdash.models import Survey as SurveyModel
from jdash.config.textmessages import TextMessages as textmessages

logger = logging.getLogger("django")


def _forbidden(message="You do not have permission to perform this action."):
    return HttpResponseForbidden(message)


def _is_legacy_file_survey_placeholder(survey):
    if not isinstance(survey, dict):
        return False

    if str(survey.get(constants.key_name_id)) != "999":
        return False

    description = str(survey.get(constants.key_name_survey_description, "")).strip()
    return (
        not survey.get(constants.key_name_created_date)
        or description.endswith(" json file")
    )


def _has_legacy_file_survey_placeholder(survey_list):
    if not isinstance(survey_list, list):
        return False
    return any(_is_legacy_file_survey_placeholder(survey) for survey in survey_list)


def _normalize_survey_list_for_display(survey_list):
    normalized_surveys = []
    for survey in survey_list or []:
        if isinstance(survey, dict) and _is_legacy_file_survey_placeholder(survey):
            survey = survey.copy()
            survey.pop(constants.key_name_id, None)
        normalized_surveys.append(survey)
    return normalized_surveys


def _has_legacy_value(value):
    if value in (None, "", [], {}):
        return False
    if isinstance(value, str):
        return value.strip().lower() not in ("", "[]", "none", "null")
    return True


def _legacy_study_json_last_updated(study_name):
    json_path = os.path.join(config.studies_folder, study_name, f"{study_name}.json")
    try:
        return datetime.fromtimestamp(os.path.getmtime(json_path))
    except OSError:
        return None


def _legacy_survey_summary(study_json, study_name=None):
    survey = study_json.get("survey") or {}
    questions = survey.get("questions") or []
    categories = survey.get("categories") or []
    return {
        "conditional_question_count": sum(
            1 for question in questions
            if _has_legacy_value(question.get("activate_question"))
            or _has_legacy_value(question.get("deactivate_question"))
        ),
        "has_time_windows": any(
            _has_legacy_value(question.get("clockTime_start"))
            or _has_legacy_value(question.get("clockTime_end"))
            or _has_legacy_value(question.get("clockTime"))
            for question in questions
        ),
        "category_count": len(categories),
        "last_updated": _legacy_study_json_last_updated(study_name) if study_name else None,
    }


def _legacy_category_rows(study_json):
    categories = ((study_json.get("survey") or {}).get("categories") or [])
    if categories:
        return categories
    return [{"categoryTitle": "", "categoryValue": 1, "didSubjectAsk": False}]


def _legacy_category_collect_flag(study_json):
    categories = ((study_json.get("survey") or {}).get("categories") or [])
    if not categories:
        return False
    return bool(categories[0].get("didSubjectAsk", False))


def _legacy_category_post_data(post_data):
    try:
        total_forms = int(post_data.get("form-TOTAL_FORMS", 0))
    except (TypeError, ValueError):
        total_forms = 0

    categories = []
    for index in range(total_forms):
        title = str(post_data.get(f"form-{index}-categoryTitle", "")).strip()
        if not title:
            continue

        try:
            value = int(post_data.get(f"form-{index}-categoryValue") or index + 1)
        except (TypeError, ValueError):
            value = index + 1

        categories.append(
            {
                "categoryTitle": title,
                "categoryValue": value,
            }
        )
    return categories


def _clear_survey_list_cache(request):
    request.session[constants.session_key_survey_details] = None
    request.session.modified = True


def _fresh_survey_list_context(request):
    context = get_all_survey_details(request.user, request.session.session_key) or {}
    context.update(context_for_survey_list_page())
    survey_list = context.get("survey_list")
    if survey_list is not None:
        survey_list = _normalize_survey_list_for_display(survey_list)
        context["survey_list"] = survey_list
        request.session[constants.session_key_survey_details] = list(survey_list)
        request.session.modified = True
    return context


@login_required
def create_survey(request, survey_id=0, question_id=0):
    """
    Handles top-level survey create, update, import, and question-delete actions.

    Args:
        request (HttpRequest): The HTTP request object with form data.
        survey_id (int, optional): ID of the survey being modified.
        question_id (int, optional): Placeholder for route compatibility.

    Returns:
        HttpResponse: Survey editor page or survey list page on failure.
    """
    context = context_for_create_survey_page(survey_id)
    protected_posts = {
        constants.button_name_upload_survey,
        constants.button_name_create_survey,
        constants.button_name_update_survey_info,
        constants.button_name_delete_question,
        constants.button_name_update_question_sort,
    }
    if request.method == constants.post_method and any(name in request.POST for name in protected_posts):
        if not permissions.can_manage_survey(request.user):
            return _forbidden()

    try:
        if constants.button_name_upload_survey in request.POST:
            form = JSONUploadForm(request.POST, request.FILES)
            if form.is_valid():
                context = upload_survey_file(request.FILES["json_file"], request.user)
        elif constants.button_name_create_survey in request.POST:
            form = SurveyForm(request.POST)
            logger.info(form.errors)
            if form.is_valid():
                form_data = get_survey_form_data(form)
                context = create_survey_from_surveyForm(form_data, request.user)
        elif constants.button_name_update_survey_info in request.POST:
            form = SurveyForm(request.POST)
            logger.debug(form.errors)
            if form.is_valid():
                form_data = get_survey_form_data(form)
                context = update_survey_from_surveyForm(form_data, survey_id)
        elif constants.button_name_delete_question in request.POST:
            survey_id = request.POST[constants.key_name_survey_id]
            question_ids = request.POST.getlist(constants.field_name_question_id)
            if question_ids:
                context = delete_questions_from_survey(question_ids, survey_id)
                error_message = context.pop(constants.key_name_error_message, None)
                if error_message:
                    messages.error(request, error_message)
            else:
                messages.error(request, _("Please select at least one question to delete."))
                context = context_for_create_survey_page(survey_id)
        elif constants.button_name_update_question_sort in request.POST:
            survey_id = int(request.POST.get(constants.key_name_survey_id, survey_id))
            question_id = int(request.POST[constants.field_name_question_id])
            questions = retrieve_all_questions_for_survey(survey_id)
            question_ids = {question["db_id"] for question in questions}
            try:
                new_sort_id = int(request.POST[constants.key_name_sortId])
            except (TypeError, ValueError):
                new_sort_id = 0
            if question_id not in question_ids:
                messages.error(request, _("create_survey_question_order_belongs_error"))
            elif new_sort_id < 1 or new_sort_id > len(questions):
                messages.error(
                    request,
                    _("create_survey_question_order_range_error") % {"total": len(questions)},
                )
            else:
                SurveyService.update_question_order(question_id, new_sort_id)
                messages.success(request, _("create_survey_question_order_success"))
            context = context_for_create_survey_page(survey_id)
        request.session[constants.session_key_survey_details] = None
    except TypeError as e:
        logger.info("TypeError: %s", e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
        return render(
            request,
            constants.survey_page,
            context=get_all_survey_details(request.user, request.session.session_key),
        )
    except IntegrityError as e:
        logger.info("IntegrityError: %s", e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
        return render(
            request,
            constants.survey_page,
            context=get_all_survey_details(request.user, request.session.session_key),
        )
    except Exception as e:
        logger.info("Unexpected Error: %s", e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
        return render(
            request,
            constants.survey_page,
            context=get_all_survey_details(request.user, request.session.session_key),
        )
    return render(request, constants.create_survey_page, context=context)


@login_required
def manage_question(request, survey_id=0, question_id=0):
    """
    Handles creation and update of survey questions and answers.

    Args:
        request (HttpRequest): The HTTP request object containing POST data.
        survey_id (int, optional): Survey identifier.
        question_id (int, optional): Question identifier.

    Returns:
        HttpResponse: Question editor or survey page.
    """
    if request.method == constants.post_method or question_id == 0:
        if not permissions.can_manage_questions(request.user):
            return _forbidden()

    context = {}
    category_details = retrieve_all_categories_for_survey(survey_id)
    form = None
    answer_formset = None
    if request.method == constants.post_method:
        logger.info(
            "manage_question POST received path=%s keys=%s data=%s",
            request.path,
            list(request.POST.keys()),
            request.POST,
        )
        form_post_data = request.POST.copy()
        form_initial = {}

        if question_id == 0:
            questions = retrieve_all_questions_for_survey(survey_id)
            next_sort_id = max((question.get("sortId", 0) for question in questions), default=0) + 1
            form_initial["sortId"] = next_sort_id
            if form_post_data.get("sortId") in (None, ""):
                form_post_data["sortId"] = str(next_sort_id)

        form = QuestionForm(form_post_data, initial=form_initial, categories=category_details)
        AnswerFormSet = formset_factory(AnswerForm)
        answer_formset = AnswerFormSet(form_post_data)

        try:
            if constants.button_name_add_question in request.POST:
                form_valid = form.is_valid()
                answer_formset_valid = answer_formset.is_valid()
                logger.info(form.errors)
                logger.info(answer_formset.errors)
                if form_valid and answer_formset_valid:
                    context = create_question_answer_for_survey(survey_id, form, answer_formset)
                    return render(request, constants.create_survey_page, context=context)
                if not form_valid:
                    messages.error(request, "Please correct the question fields before saving.")
                else:
                    messages.error(request, "Please correct the answer fields before saving the question.")
            elif constants.button_name_update_question in request.POST:
                form_valid = form.is_valid()
                answer_formset_valid = answer_formset.is_valid()
                logger.info(form.errors)
                logger.info(answer_formset.errors)
                if form_valid and answer_formset_valid:
                    context = update_question_answer_for_survey(question_id, form, answer_formset)
                    return render(request, constants.create_survey_page, context=context)
                if not form_valid:
                    messages.error(request, "Please correct the question fields before saving.")
                else:
                    messages.error(request, "Please correct the answer fields before saving the question.")
        except TypeError as e:
            logger.info("TypeError: %s", e)
            messages.error(request, f"{e} : {textmessages.error_message_to_contact_support}")
        except IntegrityError as e:
            logger.info("IntegrityError: %s", e)
            messages.error(request, f"{e} : {textmessages.error_message_to_contact_support}")
        except Exception as e:
            logger.info("Unexpected Error: %s", e)
            messages.error(request, f"{e} : {textmessages.error_message_to_contact_support}")

    context = context_for_question_page(survey_id, question_id)
    if request.method == constants.post_method:
        context[constants.key_name_question_form] = form
        context[constants.key_name_question_details][constants.key_name_answer_formset] = answer_formset
    if question_id == 0:
        return render(request, constants.create_question_page, context=context)
    return render(request, constants.edit_question_page, context=context)


@login_required
def download_survey_json(request, survey_id):
    """
    Downloads a database-backed survey JSON representation.

    Args:
        request (HttpRequest): The HTTP request object.
        survey_id (int): Survey identifier.

    Returns:
        HttpResponse: JSON attachment response.
    """
    logger.info("download_survey_json %s", survey_id)
    data = json.dumps(SurveyService.generate_json_for_download(survey_id), indent=4, ensure_ascii=False)
    response = HttpResponse(data, content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="survey.json"'
    return response


@login_required
def download_legacy_survey_json(request, study_name):
    """
    Downloads an embedded legacy file-backed survey JSON representation.
    """
    if not permissions.can_manage_survey(request.user):
        return _forbidden()

    logger.info("download_legacy_survey_json %s", study_name)
    study_json = get_json_data(study_name)
    data = json.dumps(study_json.get("survey", {}), indent=4, ensure_ascii=False)
    response = HttpResponse(data, content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="{study_name}_survey.json"'
    return response


@login_required
def manage_category_for_survey(request, survey_id):
    """
    Handles category updates for a specific survey.

    Args:
        request (HttpRequest): The HTTP request object.
        survey_id (int): Survey identifier.

    Returns:
        HttpResponse: Rendered survey creation page.
    """
    if not permissions.can_manage_categories(request.user):
        return _forbidden()

    context = {}
    try:
        collect_subject_id = request.POST.get(constants.key_name_collect_subject_id_flag, False)
        collect_flag = True if collect_subject_id == 'on' else False
        CategoryFormSet = formset_factory(CategoryForm)
        formset = CategoryFormSet(request.POST)
        logger.info("manage_category_for_survey %s", formset.errors)
        if formset.is_valid():
            category_data = get_category_form_data(formset)
            SurveyService.update_categories(survey_id, category_data["category_list"], collect_flag)
        context = context_for_create_survey_page(survey_id)
    except Exception as e:
        context = context_for_create_survey_page(survey_id)
        logger.error("manage_category_for_survey Unexpected Error %s ", e)
        messages.error(request, f"{e} : {textmessages.error_message_to_contact_support}")
    return render(request, constants.create_survey_page, context)


@login_required
def duplicate_survey(request, survey_id):
    """
    Handles duplication of an existing survey.

    Args:
        request (HttpRequest): The HTTP request object.
        survey_id (int): Survey identifier to duplicate.

    Returns:
        HttpResponse: Rendered survey list page.
    """
    if not permissions.can_duplicate_survey(request.user):
        return _forbidden()

    context = duplicate_and_create_new_survey_id(survey_id, request.user, request.session.session_key)
    return render(request, constants.survey_page, context)


@login_required
def duplicate_legacy_survey(request, study_name):
    """
    Duplicates an embedded legacy file-backed survey into a database-backed survey.
    """
    if not permissions.can_duplicate_survey(request.user):
        return _forbidden()

    try:
        study_json = get_json_data(study_name)
        survey_payload = study_json.get(constants.key_name_survey) or {}
        if not survey_payload:
            raise ValueError(_("No file-based survey found for this study."))

        survey_id = SurveyService.import_json_payload(
            json.dumps(survey_payload, ensure_ascii=False),
            request.user,
        )
        SurveyService.update_from_data(
            {
                "title": f"{study_name}_copy"[:100],
                "description": (
                    survey_payload.get(constants.key_name_survey_description)
                    or f"{study_name} json file"
                )[:1000],
                "topN": survey_payload.get(constants.key_name_topN, -1),
                "splitbyCategory": survey_payload.get("splitbyCategory", False),
                "scrolling": survey_payload.get("scrolling", "H"),
            },
            survey_id,
        )
        _clear_survey_list_cache(request)
        messages.success(
            request,
            _("File-based survey duplicated as database survey %(survey_id)s.")
            % {"survey_id": survey_id},
        )
        return render(request, constants.survey_page, context=_fresh_survey_list_context(request))
    except Exception as exc:
        logger.exception("duplicate_legacy_survey failed for study_name=%s", study_name)
        messages.error(request, f"{exc} : {textmessages.error_message_to_contact_support}")
        return render(request, constants.survey_page, context=_fresh_survey_list_context(request))


@login_required
def delete_legacy_survey(request, study_name):
    """
    Deletes the embedded legacy file-backed survey from a study JSON file.
    """
    if not permissions.can_delete_survey(request.user):
        return _forbidden()

    try:
        if request.method != constants.post_method or constants.button_name_delete_survey not in request.POST:
            messages.error(request, _("Please confirm survey deletion."))
            return render(request, constants.survey_page, context=_fresh_survey_list_context(request))

        delete_survey_from_file(study_name)
        _clear_survey_list_cache(request)
        messages.success(request, _("File-based survey deleted."))
    except Exception as exc:
        logger.exception("delete_legacy_survey failed for study_name=%s", study_name)
        messages.error(request, f"{exc} : {textmessages.error_message_to_contact_support}")

    return render(request, constants.survey_page, context=_fresh_survey_list_context(request))


@login_required
def duplicate_question(request, survey_id, question_id):
    """
    Handles duplication of a question within a survey.

    Args:
        request (HttpRequest): The HTTP request object.
        survey_id (int): Survey identifier.
        question_id (int): Question identifier.

    Returns:
        HttpResponse: Rendered survey creation page.
    """
    if not permissions.can_manage_questions(request.user):
        return _forbidden()

    context = duplicate_and_create_new_question_id(survey_id, question_id)
    return render(request, constants.create_survey_page, context=context)


@login_required
def delete_survey(request):
    """
    Handles deletion of a survey for the current user.

    Returns:
        HttpResponse: Rendered survey list page after the deletion attempt.
    """
    if not permissions.can_delete_survey(request.user):
        return _forbidden()

    try:
        if constants.button_name_delete_survey in request.POST:
            groupname = SessionManager.get_specific_session_data(
                request.session.session_key,
                constants.session_key_groupname,
                None,
            )
            logger.info("delete_survey:: id from request %s", request.POST['survey_id'])
            result = delete_survey_for_user(groupname, request.user, request.POST['survey_id'])
            request.session[constants.session_key_survey_details] = None
            if result:
                return render(
                    request,
                    constants.survey_page,
                    context=get_all_survey_details(request.user, request.session.session_key),
                )
    except Exception as e:
        logger.error("Unexpected Error %s ", e)
        messages.error(request, f"{e} : Please write to support email for assistance.")

    return render(
        request,
        constants.survey_page,
        context=get_all_survey_details(request.user, request.session.session_key),
    )


@login_required
def edit_survey(request, study_name):
    """
    Handles editing of embedded legacy survey data for older study JSON files.

    Args:
        request (HttpRequest): The HTTP request object.
        study_name (str): Study JSON file being updated.

    Returns:
        HttpResponse: Rendered legacy survey edit page or error page.
    """
    if not permissions.can_manage_survey(request.user):
        return _forbidden()

    context = {}
    context[constants.key_name_study_name] = study_name
    context[constants.key_name_survey_id] = "file"
    context[constants.key_name_survey_title] = study_name
    study_json = get_json_data(study_name)
    try:
        if "manage_categories" in request.POST:
            if not permissions.can_manage_categories(request.user):
                return _forbidden()

            collect_flag = request.POST.get(constants.key_name_collect_subject_id_flag, False) == "on"
            update_categories_in_file(
                study_name,
                _legacy_category_post_data(request.POST),
                collect_flag,
            )
            messages.success(request, _("Categories updated."))

        if constants.button_name_update_question_sort in request.POST:
            questions = (study_json.get("survey") or {}).get("questions") or []
            question_id = request.POST.get(constants.field_name_question_id)
            try:
                new_sort_id = int(request.POST.get(constants.key_name_sortId, 0))
            except (TypeError, ValueError):
                new_sort_id = 0

            if new_sort_id < 1 or new_sort_id > len(questions):
                messages.error(
                    request,
                    _("create_survey_question_order_range_error") % {"total": len(questions)},
                )
            else:
                update_question_order_in_file(study_name, question_id, new_sort_id)
                messages.success(request, _("create_survey_question_order_success"))

        if constants.button_name_update_question in request.POST:
            form_post_data = request.POST.copy()
            question_id = request.POST.get(constants.field_name_id_value)
            if form_post_data.get("sortId") in (None, ""):
                form_post_data["sortId"] = question_id
            form = QuestionForm(form_post_data)
            answer_form = AnswerForm(request.POST)
            if form.is_valid() and answer_form.is_valid():
                legacy_question_fields = {
                    "title",
                    "active",
                    "mandatory",
                    "subText",
                    "questionType",
                    "category",
                    "nextDayToAnswer",
                    "imageURL",
                    "url",
                    "frequency",
                    "clockTime",
                    "clockTime_start",
                    "clockTime_end",
                    "activate_question",
                    "deactivate_question",
                    "activation_condition",
                    "deactivation_condition",
                    "deactivateOnAnswer",
                    "deactivateOnDate",
                }
                values_to_be_updated = {
                    key: value
                    for key, value in get_question_form_data(form).items()
                    if key in legacy_question_fields
                }
                values_to_be_updated[constants.key_name_id] = question_id
                update_old_survey_details(
                    study_name,
                    values_to_be_updated,
                    answer_form.cleaned_data,
                )
                messages.success(request, _("Question updated."))
            else:
                messages.error(request, _("Please correct the question fields before saving."))

        if constants.button_name_remove_question in request.POST:
            question_ids = request.POST.getlist("question_id")
            if question_ids:
                delete_questions_from_file(study_name, question_ids)
                messages.success(
                    request,
                    _("%(count)s question(s) deleted.") % {"count": len(question_ids)},
                )
            else:
                delete_question_from_file(
                    study_name,
                    question_id=request.POST.get(constants.field_name_id_value),
                    title=request.POST.get(constants.key_name_question_title),
                )
                messages.success(request, _("Question deleted."))

        if constants.button_name_copy_question in request.POST:
            duplicate_question_in_file(
                study_name,
                request.POST.get(constants.field_name_id_value),
            )
            messages.success(request, _("Question duplicated."))

        if request.method == constants.post_method:
            study_json = get_json_data(study_name)
    except Exception as exc:
        logger.exception("edit_survey failed for study_name=%s", study_name)
        messages.error(request, f"{exc} : {textmessages.error_message_to_contact_support}")

    if constants.key_name_error_message in context:
        return render(request, constants.error_page, context)

    context[constants.key_name_json_meta] = study_json
    context[constants.key_name_questions] = (study_json.get("survey") or {}).get("questions") or []
    context["survey_summary"] = _legacy_survey_summary(study_json, study_name)
    context["legacy_category_rows"] = _legacy_category_rows(study_json)
    context["legacy_category_total"] = len(context["legacy_category_rows"])
    context[constants.key_name_collect_flag] = _legacy_category_collect_flag(study_json)
    context[constants.key_name_category_help_text] = get_help_texts_for_category_form()
    context[constants.key_name_survey_form] = SurveyForm(request.POST)
    context[constants.key_name_question_form] = QuestionForm()
    context[constants.key_name_question_help_text] = get_help_texts_for_question_form()
    context[constants.key_name_answer_form] = AnswerForm()
    return render(request, constants.edit_survey_page, context)


@login_required
def survey_list(request):
    """
    Renders the survey list page with session-based caching.

    Returns:
        HttpResponse: Rendered survey list page.
    """
    session_key = request.session.session_key
    session_data = SessionManager.get_specific_session_data(
        session_key,
        constants.session_key_survey_details,
        default=None,
    )

    if _has_legacy_file_survey_placeholder(session_data):
        request.session.pop(constants.session_key_survey_details, None)
        request.session.modified = True
        session_data = None

    if session_data is not None:
        context = {"survey_list": _normalize_survey_list_for_display(session_data)}
    else:
        context = get_all_survey_details(request.user, session_key) or {}
        survey_list = context.get("survey_list")

        if survey_list is not None:
            survey_list = _normalize_survey_list_for_display(survey_list)
            context["survey_list"] = survey_list
            request.session[constants.session_key_survey_details] = list(survey_list)
            request.session.modified = True
        else:
            logger.warning("Survey list missing in context.")
            context["survey_list"] = []
            messages.error(
                request,
                context.get(constants.key_name_error_message, "Unable to fetch survey list."),
            )
    context.update(context_for_survey_list_page())
    return render(request, constants.survey_page, context)


@login_required
def survey_audit(request, survey_id):
    """
    Renders the audit history page for a survey.

    Args:
        request (HttpRequest): The HTTP request object.
        survey_id (int): Survey identifier whose audit history is shown.

    Returns:
        HttpResponse: Rendered survey audit history page.
    """
    survey = SurveyModel.objects.get(id=survey_id)
    context = {
        "survey": survey,
        "audit_history": SurveyAuditService.get_history(survey),
    }
    return render(request, constants.survey_audit_page, context)

