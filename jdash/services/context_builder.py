import json
import logging

from django.forms.formsets import formset_factory

from jdash.config import constants as constants
from jdash.audit.services import SurveyAuditService
from jdash.services.study import get_all_study_details
from jdash.services.subject import Subject
from jdash.forms import (
    AnswerForm,
    CategoryForm,
    CreateSubjectForm,
    DeleteSubjectForm,
    JSONUploadForm,
    QuestionForm,
    RemoveSubjectsForm,
    SendNotificationForm,
    SurveyForm,
)
from jdash.services.datahelper import (
    get_blank_answer_object,
    get_help_texts_for_category_form,
    get_help_texts_for_question_form,
    get_help_texts_for_survey_form,
)
from jdash.repositories.survey_repository import (
    retrieve_all_categories_for_survey,
    retrieve_all_questions_for_survey,
    retrieve_question_details,
    retrieve_survey,
    retrieve_survey_details,
)
from jdash.utils.utils import modify_questions_list_to_string
from jdash.interface.session_manager import SessionManager
from jdash.models import (
    DeviceCatalog,
    DeviceSensor,
    Question,
    # ResolutionCatalog,
    SamplingRateCatalog,
    StudyDeviceSensor,
    UnitCatalog,
)

logger = logging.getLogger("django")


def _has_condition_question(question):
    return (
        bool(question.get("activate_question"))
        or bool(question.get("deactivate_question"))
    )


def _has_time_windows(question):
    empty_values = {None, "", "[]", "None", "none", "null"}
    return (
        question.get("clockTime_start") not in empty_values
        or question.get("clockTime_end") not in empty_values
    )


def _get_survey_last_updated(survey):
    audit_history = SurveyAuditService.get_history(survey)
    if audit_history:
        return audit_history[0].timestamp
    return survey.createdDate


def context_for_home_page(user):
    context = {}
    study_meta, stats, error_message = get_all_study_details(user)
    context[constants.key_name_study_meta] = study_meta
    context[constants.key_name_stats] = stats
    context[constants.key_name_error_message] = error_message
    return context


def context_for_add_edit_study_page(study_name, form, task_formset, study_device_formset, sensor_formsets, json_meta):
    context = {}
    context[constants.key_name_study_name] = study_name
    if "" != json_meta:
        context[constants.key_name_json_meta] = json_meta
        context[constants.key_name_number_of_subjects] = json_meta.get(constants.key_name_number_of_subjects)
        context[constants.key_name_is_survey] = True if constants.key_name_survey in json_meta else False
    else:
        context[constants.key_name_study_form] = form
    context[constants.key_name_task_formset] = task_formset
    context[constants.key_name_wbdevice_formset] = study_device_formset
    context["device_pairs"] = list(zip(study_device_formset.forms, sensor_formsets))

    context["devices_json"] = list(DeviceCatalog.objects.values("id", "name", "manufacturer", "model"))
    context["device_sensors_json"] = list(
        DeviceSensor.objects.select_related(
            "device", "sensor", "default_sampling_rate", "default_unit"
        ).values(
            "id", "device_id", "sensor_id",
            "sensor__label", "sensor__code",
            "default_sampling_rate_id", "default_unit_id",
        )
    )
    # Resolution support is currently disabled in the wearable-device UI.
    # context["resolution_json"] = list(
    #     ResolutionCatalog.objects.values("id", "value", "sensor_id")
    # )
    context["sampling_json"] = list(
        SamplingRateCatalog.objects.values("id", "value", "sensor_id")
    )
    context["unit_json"] = list(
        UnitCatalog.objects.values("id", "value", "sensor_id")
    )

    return context


def context_for_study_detail_page(study_name, session_key,subject_details=None):
    context = {}

    user_details = SessionManager.get_specific_session_data(
        session_key,
        constants.session_key_user_details,
        [],
    )
    context[constants.key_name_total_count] = Subject.count_pdfs(study_name)

    context[constants.key_name_new_subjects_form] = CreateSubjectForm()

    subject_details = subject_details or {
        constants.key_name_ids_to_be_removed: []
    }

    context[constants.key_name_remove_subjects_form] = RemoveSubjectsForm(
        receivers=subject_details.get(constants.key_name_ids_to_be_removed, [])
    )

    context[constants.key_name_notification_form] = SendNotificationForm(
        receivers=subject_details.get(constants.key_name_ids_to_be_removed, [])
    )

    context[constants.key_name_delete_subject_form] = DeleteSubjectForm()
    context[constants.field_name_email] = user_details.get(constants.field_name_email, "")

    return context


def context_for_question_page(survey_id, question_id):
    context = {}
    question_details = {}

    survey_details = retrieve_survey_details(survey_id)
    questions = retrieve_all_questions_for_survey(survey_id)
    category_details = retrieve_all_categories_for_survey(survey_id)
    context["question_category_map"] = {
        str(question.get("sortId")): str(question.get("category"))
        for question in questions
        if question.get("sortId") is not None
    }
    context[constants.key_name_survey_id] = survey_id
    context[constants.key_name_survey_title] = survey_details["title"]
    context[constants.key_name_question_id] = question_id
    context[constants.key_name_question_help_text] = get_help_texts_for_question_form()

    if question_id == 0:
        next_sort_id = max((question.get("sortId", 0) for question in questions), default=0) + 1
        context[constants.key_name_question_form] = QuestionForm(
            initial={"sortId":next_sort_id},
            categories=category_details,
        )
        AnswerFormSet = formset_factory(AnswerForm, extra=1)
        question_details[constants.key_name_answer_formset] = AnswerFormSet()
        previous_question = (
            Question.objects.filter(survey_id=survey_id)
            .order_by("-sortId")
            .first()
        )
        if previous_question:
            context["previous_question_data"] = retrieve_question_details(previous_question.id)
            context["disable_toggle"] = False
        else:
            context["disable_toggle"] = True
            context["previous_question_data"] = {}
    else:
        question_details = retrieve_question_details(question_id)

        current_sort_id = question_details.get("sortId", 0)
        if current_sort_id > 1:
            prev_q = Question.objects.filter(survey_id=survey_id, sortId=current_sort_id - 1).first()
            if prev_q:
                context["previous_question_data"] = retrieve_question_details(prev_q.id)
                context["disable_toggle"] = False
            else:
                context["previous_question_data"] = {}
                context["disable_toggle"] = True
        else:
            context["previous_question_data"] = {}
            context["disable_toggle"] = True

        for key in ("activate_question", "deactivate_question", "clockTime_start", "clockTime_end"):
            if key in question_details and isinstance(question_details[key], (list, dict)):
                question_details[key] = json.dumps(question_details[key])

        answers = question_details.get("answer", [])
        if not answers:
            answers = get_blank_answer_object()
        if question_details.get("questionType") in [1, 2]:
            answers = sorted(answers, key=lambda answer: answer.get("answerSortId", 0))
        else:
            for index, answer in enumerate(answers):
                answer.setdefault("answerSortId", index + 1)

        AnswerFormSet = formset_factory(AnswerForm, extra=0)
        answer_formset = AnswerFormSet(initial=answers)
        question_details[constants.key_name_answer_formset] = answer_formset
        context["paired"] = zip(answer_formset, answers)

        context[constants.key_name_question_form] = QuestionForm(
            initial=question_details,
            categories=category_details,
        )

    context[constants.key_name_question_details] = question_details
    return context


def context_for_create_survey_page(survey_id):
    logger.info("context_for_create_survey_page %s", survey_id)

    context = {
        constants.key_name_collect_flag: False,
    }

    if survey_id != 0:
        survey = retrieve_survey(survey_id)
        survey_details = retrieve_survey_details(survey_id)
        category_details = retrieve_all_categories_for_survey(survey_id)
        question_details_list = retrieve_all_questions_for_survey(survey_id)

        for question in question_details_list:
            question = modify_questions_list_to_string(question)

        context[constants.key_name_survey_form] = SurveyForm(data=survey_details)
        context[constants.key_name_question_form] = QuestionForm(categories=category_details)

        AnswerFormSet = formset_factory(AnswerForm, extra=1)
        for question in question_details_list:
            question[constants.key_name_answer_formset] = AnswerFormSet(initial=question["answer"])

        context[constants.key_name_survey_id] = survey_id
        context[constants.key_name_survey_title] = survey_details["title"]
        context[constants.key_name_questions] = question_details_list
        context[constants.key_name_categories] = category_details
        context["survey_summary"] = {
            "conditional_question_count": sum(
                1 for question in question_details_list if _has_condition_question(question)
            ),
            "has_time_windows": any(
                _has_time_windows(question) for question in question_details_list
            ),
            "category_count": len(category_details),
            "last_updated": _get_survey_last_updated(survey),
        }

        extra_forms = 1
        if category_details:
            extra_forms = 0
            context[constants.key_name_collect_flag] = category_details[0].get("didSubjectAsk", False)

        CategoryFormSet = formset_factory(CategoryForm, extra=extra_forms)
        context[constants.key_name_category_formset] = CategoryFormSet(initial=category_details)
        context[constants.key_name_category_help_text] = get_help_texts_for_category_form()
        context[constants.key_name_survey_help_text] = get_help_texts_for_survey_form()
    return context


def context_for_survey_list_page():
    context = {}
    context[constants.key_name_survey_jsonform] = JSONUploadForm()
    context[constants.key_name_survey_form] = SurveyForm()
    context[constants.key_name_question_form] = QuestionForm()
    context[constants.key_name_survey_help_text] = get_help_texts_for_survey_form()
    return context


