import json
import logging
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.forms.formsets import formset_factory
from django.http.response import HttpResponse
from django.shortcuts import render

from jdash.audit.services import SurveyAuditService
from jdash.services.controller import (
    create_question_answer_for_survey,
    create_survey_from_surveyForm,
    delete_question_from_file,
    delete_question_from_survey,
    duplicate_and_create_new_question_id,
    duplicate_and_create_new_survey_id,
    get_all_survey_details,
    update_old_survey_details,
    update_question_answer_for_survey,
    update_survey_from_surveyForm,
    upload_survey_file,
)
from jdash.services.survey import Survey as SurveyService
from jdash.forms import AnswerForm, CategoryForm, JSONUploadForm, QuestionForm, SurveyForm
from jdash.config import constants as constants
from jdash.services.context_builder import (
    context_for_create_survey_page,
    context_for_question_page,
    context_for_survey_list_page,
)
from jdash.services.datahelper import (
    get_category_form_data,
    get_question_form_data,
    get_survey_form_data,
)
from jdash.repositories.survey_repository import delete_survey_for_user
from jdash.utils.fileutils import get_json_data
from jdash.interface.session_manager import SessionManager
from jdash.models import Survey as SurveyModel
from jdash.config.textmessages import TextMessages as textmessages

logger = logging.getLogger("django")


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
            question_id = request.POST[constants.field_name_question_id]
            context = delete_question_from_survey(question_id, survey_id)
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
    context = {}
    form = QuestionForm(request.POST)
    AnswerFormSet = formset_factory(AnswerForm)
    answer_formset = AnswerFormSet(request.POST)

    logger.info("POST data received: %s", request.POST)

    try:
        if constants.button_name_add_question in request.POST:
            logger.info(form.errors)
            if form.is_valid():
                context = create_question_answer_for_survey(survey_id, form, answer_formset)
                return render(request, constants.create_survey_page, context=context)
        elif constants.button_name_update_question in request.POST:
            logger.info(form.errors)
            if form.is_valid():
                context = update_question_answer_for_survey(question_id, form, answer_formset)
                return render(request, constants.create_survey_page, context=context)
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
def manage_category_for_survey(request, survey_id):
    """
    Handles category updates for a specific survey.

    Args:
        request (HttpRequest): The HTTP request object.
        survey_id (int): Survey identifier.

    Returns:
        HttpResponse: Rendered survey creation page.
    """
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
    context = duplicate_and_create_new_survey_id(survey_id, request.user, request.session.session_key)
    return render(request, constants.survey_page, context)


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
    context = duplicate_and_create_new_question_id(survey_id, question_id)
    return render(request, constants.create_survey_page, context=context)


@login_required
def delete_survey(request):
    """
    Handles deletion of a survey for the current user.

    Returns:
        HttpResponse: Rendered survey list page after the deletion attempt.
    """
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
    context = {}
    context[constants.key_name_study_name] = study_name
    study_json = get_json_data(study_name)
    if constants.button_name_update_question in request.POST:
        values_to_be_updated = {}
        form = QuestionForm(request.POST)
        answerForm = AnswerForm(request.POST)
        if form.is_valid():
            values_to_be_updated = get_question_form_data(form)
            values_to_be_updated[constants.key_name_id] = request.POST[constants.field_name_id_value]
            update_old_survey_details(study_name, values_to_be_updated)

    if constants.button_name_remove_question in request.POST:
        study_json = delete_question_from_file(study_name, request.POST[constants.key_name_question_title])

    if constants.key_name_error_message in context:
        return render(request, constants.error_page, context)

    context[constants.key_name_json_meta] = study_json
    context[constants.key_name_survey_form] = SurveyForm(request.POST)
    context[constants.key_name_question_form] = QuestionForm()
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

    if session_data is not None:
        context = {"survey_list": session_data}
    else:
        context = get_all_survey_details(request.user, session_key) or {}
        survey_list = context.get("survey_list")

        if survey_list is not None:
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
