import json
import logging
from operator import itemgetter

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import F

from jdash.config import constants as constants
from jdash.interface.session_manager import SessionManager
from jdash.models import (
    Answer as answerModel,
    Category as categoryModel,
    Question as questionModel,
    Study as studymodel,
    Survey as surveyModel,
)
from jdash.utils.utils import (
    answer_download_serializer,
    answer_serializer,
    category_serializer,
    custom_serializer,
    question_db_serializer,
    question_serializer,
    survey_serializer,
)

logger = logging.getLogger("django")


def create_new_survey_in_db(form, user):
    """Create a copied survey row in the database."""
    owner = User.objects.get(username=user.username)
    logger.info("create_new_survey_in_db %s", owner.id)
    survey = surveyModel.objects.create(
        title=form["title"] + "_copy",
        description=form["description"],
        topN=form["topN"],
        splitbyCategory=form["splitbyCategory"] if "splitbyCategory" in form else 0,
        scrolling=form["scrolling"] if "scrolling" in form else "H",
        owner_id=owner.id,
    )
    return survey


def update_survey_info_in_db(form, survey_id):
    """Update top-level survey fields."""
    survey = surveyModel.objects.get(id=survey_id)
    survey.title = form["title"]
    survey.description = form["description"]
    survey.topN = form["topN"]
    survey.splitbyCategory = form["splitbyCategory"] if "splitbyCategory" in form else 0
    survey.scrolling = form["scrolling"] if "scrolling" in form else "H"
    survey.save()
    return survey


def create_survey_in_db(study_name, survey_dict, user):
    """Create a survey and its questions/answers from imported JSON data."""
    if constants.key_name_survey in survey_dict:
        survey_dict = survey_dict[constants.key_name_survey]

    survey = surveyModel.objects.create(
        title=study_name,
        description="",
        topN=survey_dict[constants.key_name_topN]
        if constants.key_name_topN in survey_dict
        else -1,
        splitbyCategory=survey_dict["splitbyCategory"] if "splitbyCategory" in survey_dict else 0,
        scrolling=survey_dict["scrolling"] if "scrolling" in survey_dict else "H",
        owner=user,
    )
    logger.info("create_survey_in_db::start::%s", survey)

    if "categories" in survey_dict:
        create_categories_in_db_from_data(survey.id, survey_dict["categories"])

    for question_data in survey_dict["questions"]:
        if question_data["clockTime_start"].strip():
            question_data["clockTime_start"] = [
                int(x) for x in question_data["clockTime_start"].split(";")
            ]
        if question_data["clockTime_end"].strip():
            question_data["clockTime_end"] = [
                int(x) for x in question_data["clockTime_end"].split(";")
            ]
        if question_data["activate_question"].strip():
            if question_data["activate_question"] != "" and ";" in question_data["activate_question"]:
                question_data["activate_question"] = [
                    int(x) for x in question_data["activate_question"].split(";")
                ]
        if question_data["deactivate_question"].strip():
            if question_data["deactivate_question"] != "" and ";" in question_data["deactivate_question"]:
                question_data["deactivate_question"] = [
                    int(x) for x in question_data["deactivate_question"].split(";")
                ]

        if (
            question_data[constants.field_name_clockTime] > 0
            and question_data[constants.field_name_clockTime_start] == ""
            and question_data[constants.field_name_clockTime_end] == ""
        ):
            question_data[constants.field_name_clockTime_start] = [
                int(question_data[constants.field_name_clockTime])
            ]

        question = questionModel.objects.create(
            survey=survey,
            title=question_data["title"],
            active=1,
            sortId=question_data["id"],
            subText=question_data["subText"],
            frequency=question_data["frequency"],
            clockTime=question_data["clockTime"],
            clockTime_start=question_data["clockTime_start"],
            clockTime_end=question_data["clockTime_end"],
            nextDayToAnswer=question_data["nextDayToAnswer"],
            category=question_data["category"],
            imageURL=question_data["imageURL"],
            url=question_data["url"],
            questionType=question_data["questionType"],
            deactivateOnAnswer=question_data["deactivateOnAnswer"],
            deactivateOnDate=question_data["deactivateOnDate"],
            activate_question=question_data["activate_question"],
            deactivate_question=question_data["deactivate_question"],
            activation_condition=question_data["activation_condition"],
            deactivation_condition=question_data["deactivation_condition"],
            clockTime_timezone="Europe/Berlin",
        )
        logger.info("create_question_in_db::done::%s", question.id)
        if "answer" in question_data:
            for answer_data in question_data["answer"]:
                create_answer_from_file_in_db(question.id, answer_data)

    logger.info("create_survey_in_db::end %s", survey)
    return survey


def create_answer_from_file_in_db(question_id, answer_data):
    """Create an answer row from imported survey JSON."""
    logger.info("creating answer %s", answer_data)
    answerModel.objects.create(
        question_id=question_id,
        answerSortId=answer_data["id"],
        text=answer_data["text"],
        answerSubText=answer_data["subText"] if "subText" in answer_data else "N",
        value=answer_data["value"],
        defaultValue=answer_data["defaultValue"],
        stepSize=answer_data["stepSize"],
        minValue=answer_data["minVal"],
        maxValue=answer_data["maxVal"],
        minText=answer_data["minText"],
        maxText=answer_data["maxText"],
    )
    logger.info("create_answer_in_db::successful:end")


def create_answer_in_db(question_id, answer_data):
    """Create an answer row from normalized form data."""
    logger.info("create_answer_in_db:::start %s", answer_data)
    answer_data["answerSortId"] = (
        answer_data["id"] if "id" in answer_data else answer_data["answerSortId"]
    )
    answer_data["answerSubText"] = answer_data["subText"] if "subText" in answer_data else "N"
    answer_data["minValue"] = (
        answer_data["minVal"] if "minVal" in answer_data else answer_data["minValue"]
    )
    answer_data["maxValue"] = (
        answer_data["maxVal"] if "maxVal" in answer_data else answer_data["maxValue"]
    )
    answerModel.objects.create(
        question_id=question_id,
        answerSortId=answer_data["answerSortId"],
        text=answer_data["text"],
        answerSubText=answer_data["answerSubText"],
        value=answer_data["value"],
        defaultValue=answer_data["defaultValue"],
        stepSize=answer_data["stepSize"],
        minValue=answer_data["minValue"],
        maxValue=answer_data["maxValue"],
        minText=answer_data["minText"],
        maxText=answer_data["maxText"],
    )
    logger.info("create_answer_in_db::successful:end")


def create_question_answers_in_db(survey_id, question_data):
    """Create a survey question and its answers."""
    question = questionModel.objects.create(
        survey_id=survey_id,
        title=question_data["title"],
        active=1,
        sortId=question_data["id"],
        subText=question_data["subText"],
        frequency=question_data["frequency"],
        clockTime=question_data["clockTime"],
        clockTime_start=question_data["clockTime_start"],
        clockTime_end=question_data["clockTime_end"],
        nextDayToAnswer=question_data["nextDayToAnswer"],
        category=question_data["category"],
        imageURL=question_data["imageURL"],
        url=question_data["url"],
        questionType=question_data["questionType"],
        deactivateOnAnswer=question_data["deactivateOnAnswer"],
        deactivateOnDate=question_data["deactivateOnDate"],
        activate_question=question_data["activate_question"],
        deactivate_question=question_data["deactivate_question"],
        activation_condition=question_data["activation_condition"],
        deactivation_condition=question_data["deactivation_condition"],
        clockTime_timezone=question_data["clockTime_timezone"],
    )
    logger.info("create_question_in_db::done::%s", question.id)

    if "answer" in question_data:
        for answer_data in question_data["answer"]:
            create_answer_in_db(question.id, answer_data)
            logger.info("create_answer_in_db::successful:end")
    return question


def update_answer_in_db(form_data, answer_id):
    """Update an answer row."""
    logger.info("update_answer_in_db ::%s :: %s", form_data, answer_id)
    answer = answerModel.objects.get(id=answer_id)
    answer.text = form_data["text"]
    answer.answerSubText = form_data["answerSubText"]
    answer.answerSortId = form_data["answerSortId"]
    answer.value = form_data["value"]
    answer.defaultValue = form_data["defaultValue"]
    answer.minValue = form_data["minValue"]
    answer.maxValue = form_data["maxValue"]
    answer.stepSize = form_data["stepSize"]
    answer.maxText = form_data["maxText"]
    answer.minText = form_data["minText"]
    answer.save()


def delete_answer_in_db(answer_id):
    """Delete an answer row by id."""
    try:
        logger.info("delete_answer_in_db ::%s", answer_id)
        answerModel.objects.get(id=answer_id).delete()
    except answerModel.DoesNotExist:
        logger.error("Answer with id %s does not exist for question id %s", answer_id)
        return False


def update_question_in_db(question_id, question_data):
    """Update a question row."""
    logger.info("update_question_in_db %s", question_data)

    question_data["activate_question"] = question_data.get("activate_question") or []
    question_data["deactivate_question"] = question_data.get("deactivate_question") or []
    question_data["clockTime_start"] = question_data.get("clockTime_start") or []
    question_data["clockTime_end"] = question_data.get("clockTime_end") or []

    question = questionModel.objects.get(id=question_id)
    question.title = question_data["title"]
    question.subText = question_data["subText"]
    question.active = 1 if question_data["active"] else 0
    question.sortId = question_data["sortId"]
    question.frequency = question_data["frequency"]
    question.clockTime = question_data["clockTime"]
    question.clockTime_start = question_data["clockTime_start"]
    question.clockTime_end = question_data["clockTime_end"]
    question.nextDayToAnswer = question_data["nextDayToAnswer"]
    question.category = question_data["category"]
    question.imageURL = question_data["imageURL"]
    question.url = question_data["url"]
    question.questionType = question_data["questionType"]
    question.deactivateOnAnswer = question_data["deactivateOnAnswer"]
    question.deactivateOnDate = question_data["deactivateOnDate"]
    question.activate_question = question_data["activate_question"]
    question.deactivate_question = question_data["deactivate_question"]
    question.activation_condition = question_data["activation_condition"]
    question.deactivation_condition = question_data["deactivation_condition"]
    question.clockTime_timezone = question_data.get("clockTime_timezone", "Europe/Berlin")
    question.save()


def delete_survey_for_user(group_name, user, survey_id):
    """Delete a survey for the current user/group context."""
    if "administrator" in group_name:
        result = surveyModel.objects.filter(id=survey_id).all()
    else:
        result = surveyModel.objects.filter(owner=user).filter(id=survey_id).all()
    result.delete()
    return True


def delete_question_from_db(question_id: int, survey_id: int) -> bool:
    """Delete a question and compact subsequent sort ids."""
    with transaction.atomic():
        try:
            question = (
                questionModel.objects.select_for_update().get(
                    id=question_id,
                    survey_id=survey_id,
                )
            )
        except questionModel.DoesNotExist:
            return False

        removed_pos = question.sortId
        question.delete()
        questionModel.objects.filter(
            survey_id=survey_id,
            sortId__gt=removed_pos,
        ).update(sortId=F("sortId") - 1)

    return True


def retrieve_all_questions_for_survey(survey_id):
    """Return all questions and their answers for a survey."""
    queryset = questionModel.objects.filter(survey__pk=survey_id).values()
    question_list = json.loads(question_db_serializer(queryset))
    for question in question_list:
        answers = answerModel.objects.filter(question_id=question["db_id"]).values()
        question["answer"] = json.loads(answer_serializer(answers))
    sorted_questions_list = json.dumps(sorted(question_list, key=itemgetter("id")))
    return json.loads(sorted_questions_list)


def retrieve_download_questions_for_survey(survey_id):
    """Return survey questions serialized for JSON download."""
    queryset = questionModel.objects.filter(survey__pk=survey_id).values()
    question_list = json.loads(question_serializer(queryset))
    for question in question_list:
        answers = answerModel.objects.filter(question_id=question["db_id"]).values()
        question["answer"] = json.loads(answer_download_serializer(answers))
    sorted_questions_list = json.dumps(sorted(question_list, key=itemgetter("id")))
    return json.loads(sorted_questions_list)


def retrieve_all_answers_for_questions(question_id):
    """Return serialized answers for a question."""
    answers = answerModel.objects.filter(question_id=question_id).values()
    return json.loads(answer_serializer(answers))


def retrieve_all_categories_for_survey(survey_id):
    """Return serialized categories for a survey."""
    queryset = categoryModel.objects.filter(survey__pk=survey_id).order_by("categoryValue").values()
    category_list = json.loads(category_serializer(queryset))
    logger.info("retrieve_all_categories_for_survey %s", category_list)
    return category_list


def retrieve_survey(survey_id):
    """Return a survey model instance."""
    return surveyModel.objects.get(id=survey_id)


def retrieve_question(question_id):
    """Return a question model instance."""
    return questionModel.objects.get(id=question_id)


def retrieve_survey_details(survey_id):
    """Return serialized survey details."""
    data = surveyModel.objects.filter(id=survey_id).values()
    return json.loads(survey_serializer(data))[0]


def retrieve_question_details(question_id):
    """Return serialized question details including answers."""
    data = questionModel.objects.filter(id=question_id).values()
    question_json = json.loads(question_db_serializer(data))[0]
    logger.info("retrieve_question_details:::%s", question_json)
    question_json["answer"] = retrieve_all_answers_for_questions(question_id)
    for answer in question_json["answer"]:
        answer["answerSortId"] = answer["id"]
    return question_json


def retrieve_questions_greater_than_sortId(survey_id, sort_id):
    """Return questions in a survey after the given sort position."""
    questions = questionModel.objects.filter(survey_id=survey_id, sortId__gt=sort_id).values()
    question_json = json.loads(question_serializer(questions))
    logger.info("retrieve_questions_greater_than_sortId:::%s", question_json)
    return question_json


def retrieve_all_survey_for_user(user, session_key):
    """Return all surveys visible to a user in the current session context."""
    queryset = surveyModel.objects.none()
    group_name = SessionManager.get_specific_session_data(
        session_key,
        constants.session_key_groupname,
        None,
    )
    ema_studies = SessionManager.get_specific_session_data(
        session_key,
        constants.session_key_studies_ema,
        [],
    )

    if "administrator" in group_name:
        queryset = surveyModel.objects.values()
        survey_list = json.loads(survey_serializer(queryset))
        for obj in survey_list:
            study_details = studymodel.objects.filter(survey=obj["id"]).values()
            if study_details:
                obj["study_name"] = ", ".join([study["title"] for study in study_details])
            category_titles = list(
                categoryModel.objects.filter(survey_id=obj["id"])
                .order_by("categoryValue")
                .values_list("categoryTitle", flat=True)
            )
            obj["category_names"] = ", ".join(category_titles)
        return survey_list

    return get_list_surveys_for_user(user, ema_studies)


def get_list_surveys_for_user(user, ema_studies):
    """Return visible surveys for a non-admin user."""
    unique_surveys = set()
    surveys = []
    queryset = surveyModel.objects.filter(owner=user).values()

    if queryset:
        for survey in json.loads(survey_serializer(queryset)):
            study_details = studymodel.objects.filter(survey=survey["id"]).values()
            if study_details:
                survey["study_name"] = ", ".join([study["title"] for study in study_details])
            category_titles = list(
                categoryModel.objects.filter(survey_id=survey["id"])
                .order_by("categoryValue")
                .values_list("categoryTitle", flat=True)
            )
            survey["category_names"] = ", ".join(category_titles)
            if survey["id"] not in unique_surveys:
                unique_surveys.add(survey["id"])
                surveys.append(survey)

    for studyname in ema_studies:
        data = studymodel.objects.filter(title=studyname).values()
        jsondata = json.loads(custom_serializer(data))[0]
        survey_queryset = surveyModel.objects.filter(id=jsondata["survey"]).values()
        if survey_queryset:
            for survey in json.loads(survey_serializer(survey_queryset)):
                survey["study_name"] = jsondata["title"]
                category_titles = list(
                    categoryModel.objects.filter(survey_id=survey["id"])
                    .order_by("categoryValue")
                    .values_list("categoryTitle", flat=True)
                )
                survey["category_names"] = ", ".join(category_titles)
                if survey["id"] not in unique_surveys:
                    unique_surveys.add(survey["id"])
                    surveys.append(survey)

    return surveys


def get_categories_from_db(survey_id):
    """Return queryset of categories for a survey."""
    categories_list = categoryModel.objects.filter(survey_id=survey_id)
    logger.debug("get_categories_from_db::successful:end")
    return categories_list


def create_categories_in_db(survey_id, category_data):
    """Create survey categories from form data."""
    logger.info("create_categories_in_db:::start %s", category_data)
    for data in category_data["category_list"]:
        categoryModel.objects.create(
            survey_id=survey_id,
            categoryValue=int(data["categoryValue"]),
            categoryTitle=data["categoryTitle"],
            didSubjectAsk=data["didSubjectAsk"],
        )
    logger.info("create_categories_in_db::successful:end")


def create_categories_in_db_from_data(survey_id, category_data):
    """Create survey categories from JSON/import data."""
    for data in category_data:
        categoryModel.objects.create(
            survey_id=survey_id,
            categoryValue=int(data["categoryValue"]),
            categoryTitle=data["categoryTitle"],
            didSubjectAsk=data["didSubjectAsk"],
        )
    logger.info("create_categories_in_db::successful:end")


def get_question_by_sortid(survey_id, sort_id):
    """Retrieve a question by survey id and sort id."""
    question = questionModel.objects.filter(survey_id=survey_id, sortId=sort_id).values()
    if question:
        result = json.loads(question_db_serializer(question))[0]
        logger.info("get_question_by_sortid::question: %s", result)
        return result
    return None
