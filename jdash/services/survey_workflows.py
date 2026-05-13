import logging

from jdash.config import constants as constants
from jdash.exceptions.controllerexceptions import controller_error_message
from jdash.repositories.survey_repository import (
    create_categories_in_db_from_data,
    create_new_survey_in_db,
    create_question_answers_in_db,
    retrieve_all_categories_for_survey,
    retrieve_all_questions_for_survey,
    retrieve_all_survey_for_user,
    retrieve_question_details,
    retrieve_survey_details,
)
from jdash.services.context_builder import (
    context_for_create_survey_page,
    context_for_survey_list_page,
)
from jdash.services.datahelper import (
    get_answer_form_data,
    get_question_form_data,
)
from jdash.services.survey import Survey
from jdash.utils.fileutils import open_study_json, save_study_json
from jdash.utils.utils import get_survey_list

logger = logging.getLogger("django")


def get_all_survey_details(user, session_key):
    """
    Retrieve all survey details for a user and session.
    """
    context = {}
    survey_list_details = []
    try:
        survey_from_db = retrieve_all_survey_for_user(user, session_key)
        if len(survey_from_db) > 0:
            for survey in survey_from_db:
                survey_list_details.append(survey)

        survey_files_list = get_survey_list(session_key)
        if survey_files_list is not None:
            for survey in survey_files_list:
                survey_list_details.append(survey)

        context["survey_list"] = survey_list_details
    except Exception as exc:
        logger.info("Exception occured while fecthing surveys %s", exc)
        context[constants.key_name_error_message] = "get_all_survey_details:: Exception occured"
    return context


def create_question_answer_for_survey(survey_id, form, answer_formset):
    """
    Create a new question and its answers for a survey.
    """
    logger.info("create_question_answer_for_survey %s", survey_id)
    question_obj = get_question_form_data(form)
    answers = []
    if answer_formset.is_valid():
        form_data = get_answer_form_data(answer_formset, int(question_obj["questionType"]))
        answers = form_data["answers"]
    Survey.create_question_with_answers(survey_id, question_obj, answers)
    return context_for_create_survey_page(survey_id)


def update_question_answer_for_survey(question_id, form, answer_formset):
    """
    Update a survey question and replace its associated answers.
    """
    question_obj = get_question_form_data(form)
    answers = []
    if answer_formset.is_valid():
        form_data = get_answer_form_data(answer_formset, int(question_obj["questionType"]))
        answers = form_data["answers"]
    survey_id = Survey.update_question_with_answers(question_id, question_obj, answers)
    context = context_for_create_survey_page(survey_id)
    logger.info("update_question_answer_for_survey::: %s", context["survey_id"])
    return context


def update_old_survey_details(study_name, values_to_be_updated):
    """
    Update legacy file-backed survey content embedded in a study JSON file.
    """
    study_json = open_study_json(study_name)
    question_id = values_to_be_updated["id"]
    Survey.update_question(question_id, title="Updated Question Title", sub_text="New subtext")
    answer_index_to_update = 1
    Survey.update_answer(
        question_id,
        answer_index_to_update,
        answer_text="Updated Answer Text",
        answer_value=3.14,
    )
    updated_survey_json = Survey.to_json()
    save_study_json(study_name, updated_survey_json)
    return True


def create_survey_from_surveyForm(form_data, user):
    """
    Create a survey from normalized form data and return editor context.
    """
    try:
        survey_id = Survey.create_from_data(form_data, user)
        return context_for_create_survey_page(survey_id)
    except Exception as exc:
        logger.exception("create_survey_from_surveyForm failed")
        context = context_for_survey_list_page()
        context[constants.key_name_error_message] = controller_error_message(exc)
        return context


def update_survey_from_surveyForm(form_data, survey_id):
    """
    Update survey metadata from normalized form data and return editor context.
    """
    try:
        survey_id = Survey.update_from_data(form_data, survey_id)
        return context_for_create_survey_page(survey_id)
    except Exception as exc:
        logger.exception("update_survey_from_surveyForm failed for survey_id=%s", survey_id)
        context = context_for_create_survey_page(survey_id)
        context[constants.key_name_error_message] = controller_error_message(exc)
        return context


def upload_survey_json_file(survey_str, user):
    """
    Import a survey from a JSON payload and return the created survey context.
    """
    try:
        survey_id = Survey.import_json_payload(survey_str, user)
        return context_for_create_survey_page(survey_id)
    except Exception as exc:
        logger.exception("upload_survey_json_file failed")
        context = context_for_survey_list_page()
        context[constants.key_name_error_message] = controller_error_message(exc)
        return context


def upload_survey_file(uploaded_file, user):
    """
    Import a survey from an uploaded JSON, CSV, or Excel file.
    """
    try:
        survey_id = Survey.import_file(uploaded_file, user)
        return context_for_create_survey_page(survey_id)
    except Exception as exc:
        logger.exception("upload_survey_file failed for filename=%s", getattr(uploaded_file, "name", ""))
        context = context_for_survey_list_page()
        context[constants.key_name_error_message] = controller_error_message(exc)
        return context


def delete_question_from_survey(question_id, survey_id):
    """
    Delete a question from a survey and return refreshed editor context.
    """
    try:
        logger.info("delete_question_from_survey %s", question_id)
        Survey.delete_question(question_id, survey_id)
        return context_for_create_survey_page(survey_id)
    except Exception as exc:
        logger.exception(
            "delete_question_from_survey failed for question_id=%s survey_id=%s",
            question_id,
            survey_id,
        )
        context = context_for_create_survey_page(survey_id)
        context[constants.key_name_error_message] = controller_error_message(exc)
        return context


def delete_question_from_file(study_name, title):
    """
    Delete a question from a legacy file-backed survey payload.
    """
    study_json = open_study_json(study_name)
    question_list = study_json["survey"]["questions"]
    for question in question_list:
        if question["title"] == title:
            question_list.remove(question)
    return study_json


def duplicate_and_create_new_survey_id(source_survey_id, user, session_key):
    """
    Duplicate a survey and all of its questions, answers, and categories.
    """
    try:
        survey_details = retrieve_survey_details(source_survey_id)
        questions = retrieve_all_questions_for_survey(source_survey_id)
        categories = retrieve_all_categories_for_survey(source_survey_id)
        new_survey = create_new_survey_in_db(survey_details, user)
        logger.info("New survey with id %s has been created", new_survey.id)

        for question_data in questions:
            create_question_answers_in_db(new_survey.id, question_data)
        if len(categories) > 0:
            create_categories_in_db_from_data(new_survey.id, categories)
        context = get_all_survey_details(user, session_key)
        context.update(context_for_survey_list_page())
    except Exception as exc:
        logger.exception(
            "duplicate_and_create_new_survey_id failed for source_survey_id=%s",
            source_survey_id,
        )
        context = get_all_survey_details(user, session_key)
        context[constants.key_name_error_message] = controller_error_message(exc)
    return context


def duplicate_and_create_new_question_id(survey_id, source_question_id):
    """
    Duplicate a question and its answers within the selected survey.
    """
    try:
        questions_of_survey = retrieve_all_questions_for_survey(survey_id)
        question_data = retrieve_question_details(source_question_id)
        question_data["id"] = len(questions_of_survey) + 1
        question = create_question_answers_in_db(survey_id, question_data)
        new_sequence_id = len(questions_of_survey) + 1
        Survey.update_question_order(question.id, new_sequence_id)
        return context_for_create_survey_page(survey_id)
    except Exception as exc:
        logger.exception(
            "duplicate_and_create_new_question_id failed for survey_id=%s source_question_id=%s",
            survey_id,
            source_question_id,
        )
        context = context_for_create_survey_page(survey_id)
        context[constants.key_name_error_message] = controller_error_message(exc)
        return context
