###########################################################################
####           survey.py
####           This file contains all the service methods related to surveys.
####           Initial version written by mnarava.
####           Refactored and extended for clarity and robustness.
####
###########################################################################

import json
import logging
import os
import tempfile
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from jdash.config import constants as constants
from jdash.repositories.survey_repository import (
    create_new_survey_in_db,
    create_question_answers_in_db,
    create_survey_in_db,
    delete_question_from_db,
    get_categories_from_db,
    retrieve_download_questions_for_survey,
    retrieve_question,
    retrieve_question_details,
    retrieve_survey_details,
    create_answer_in_db,
    retrieve_all_categories_for_survey,
    retrieve_all_questions_for_survey,
    retrieve_all_answers_for_questions,
    update_question_in_db,
    update_survey_info_in_db,
    get_question_by_sortid,
    delete_answer_in_db,
)
from jdash.utils.fileutils import open_study_json, save_study_json
from jdash.utils.utils import normalize_question_data_defaults,coerce_bool
from jdash.utils.surveyFileToJSON import SurveyFileToJSONConverter
from jdash.models import Question, Category
logger = logging.getLogger("django")


class Survey:
    """
    Class representing a Survey.

    Attributes:
        id (int): Survey identifier.
        title (str): Title of the survey.
        description (str): Description of the survey.
        splitbyCategory (bool): Flag to indicate split by category.
        scrolling (bool): Flag indicating scrolling behavior.
        topN (int): Limit for top N responses.
        questions (dict): Questions mapped by their IDs.
    """

    def __init__(self, id, title, description, splitbyCategory=None, scrolling=None, topN=None):
        """
        Initialize an in-memory survey representation.

        Args:
            id (int): Survey identifier.
            title (str): Survey title.
            description (str): Survey description.
            splitbyCategory (bool, optional): Whether the survey is split by category.
            scrolling (bool, optional): Whether scrolling is enabled in the client.
            topN (int, optional): Top-N setting for survey display.
        """
        self.id = id
        self.title = title
        self.description = description
        self.splitbyCategory = splitbyCategory
        self.scrolling = scrolling
        self.topN = topN
        self.questions = {}

    def add_question(self, question_dict):
        """
        Add a question to the survey.

        Args:
            question_dict (dict): Dictionary containing question details.

        Notes:
            The question ID must be present in the dictionary under key 'id'.
            Initializes an empty dictionary for answers.
        """
        question_id = question_dict.get('id')
        if question_id is None:
            logger.warning("Question dict missing 'id', cannot add question.")
            return

        self.questions[question_id] = {
            'id': question_id,
            'title': question_dict.get('title') or question_dict.get('text'),
            'questionType': question_dict.get('questionType') or question_dict.get('type'),
            'mandatory': coerce_bool(question_dict.get('mandatory'), default=False),
            'subText': question_dict.get('subText', ''),
            'category': question_dict.get('category'),
            'frequency': question_dict.get('frequency'),
            'clockTime': question_dict.get('clockTime'),
            'nextDayToAnswer': question_dict.get('nextDayToAnswer'),
            'imageURL': question_dict.get('imageURL'),
            'url': question_dict.get('url'),
            'deactivateOnAnswer': question_dict.get('deactivateOnAnswer'),
            'deactivateOnDate': question_dict.get('deactivateOnDate'),
            'answers': {}  # Stored as dict keyed by answer ID
        }

    def add_answer_to_question(self, question_id, answer_dict):
        """
        Add an answer option to a specific question.

        Args:
            question_id (int): ID of the question to add answer to.
            answer_dict (dict): Dictionary containing answer details.

        Notes:
            The answer dictionary must contain an 'id' key.
        """
        if question_id not in self.questions:
            logger.warning(f"Question ID {question_id} not found, cannot add answer.")
            return

        answer_id = answer_dict.get('id')
        if answer_id is None:
            logger.warning("Answer dict missing 'id', cannot add answer.")
            return

        self.questions[question_id]['answers'][answer_id] = {
            'id': answer_id,
            'answerText': answer_dict.get('answerText') or answer_dict.get('text', ''),
            'answerValue': answer_dict.get('answerValue') or answer_dict.get('value'),
            'defaultValue': answer_dict.get('defaultValue'),
            'stepSize': answer_dict.get('stepSize'),
            'minValue': answer_dict.get('minValue'),
            'maxValue': answer_dict.get('maxValue'),
            'minText': answer_dict.get('minText', ''),
            'maxText': answer_dict.get('maxText', ''),
        }

    def update_question(self, question_id, question_dict):
        """
        Update existing question details.

        Args:
            question_id (int): ID of the question to update.
            question_dict (dict): Dictionary with keys for fields to update.

        Notes:
            Only updates provided fields that are not None.
        """
        if question_id not in self.questions:
            logger.warning(f"Question ID {question_id} not found, cannot update.")
            return

        question = self.questions[question_id]
        for key in [
            'title', 'questionType', 'subText', 'category', 'frequency',
            'clockTime', 'nextDayToAnswer', 'imageURL', 'url',
            'deactivateOnAnswer', 'deactivateOnDate', 'mandatory', 'answers'
        ]:
            if key in question_dict and question_dict[key] is not None:
                question[key] = question_dict[key]

    def to_json(self):
        """
        Convert the survey to a JSON-serializable dictionary.

        Returns:
            dict: Survey data including questions and their answers.
        """
        survey_data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'splitbyCategory': self.splitbyCategory,
            'scrolling': self.scrolling,
            'topN': self.topN,
            'questions': [
                {
                    **q,
                    'answers': list(q['answers'].values())
                }
                for q in self.questions.values()
            ],
        }
        return survey_data

    @staticmethod
    def from_json(data):
        """
        Create a Survey object from a JSON dictionary.

        Args:
            data (dict): Survey data dictionary.

        Returns:
            Survey: Constructed Survey object.
        """
        survey = Survey(
            data.get('id'),
            data.get('title'),
            data.get('description'),
            data.get('splitbyCategory'),
            data.get('scrolling'),
            data.get('topN')
        )
        for question in data.get('questions', []):
            survey.add_question(question)
            for answer in question.get('answers', []):
                survey.add_answer_to_question(question.get('id'), answer)
        return survey
    @classmethod
    def generate_json_for_download(cls, survey_id):
        """
        Generate a JSON representation of the survey suitable for download.
        """
        logger.info("Survey.generate_json_for_download called for survey_id=%s", survey_id)
        survey_json = {}
        question_data = retrieve_download_questions_for_survey(survey_id)
        category_data = retrieve_all_categories_for_survey(survey_id)
        survey_details = retrieve_survey_details(survey_id)

        survey_json[constants.key_name_questions] = question_data
        survey_json[constants.key_name_categories] = category_data
        survey_json['id'] = survey_details['id']
        survey_json['title'] = survey_details['title']
        survey_json['description'] = survey_details['description']
        survey_json['topN'] = survey_details.get('topN', 0)
        survey_json['splitbyCategory'] = survey_details.get('splitbyCategory', False)
        survey_json['scrolling'] = survey_details.get('scrolling', False)

        logger.debug("Survey.generate_json_for_download payload=%s", survey_json)
        logger.info("Survey.generate_json_for_download finished for survey_id=%s", survey_id)
        logger.debug("Survey.generate_json_for_download return_value=%s", survey_json)
        return survey_json

    @classmethod
    def generate_json_for_study(cls, survey_id):
        """
        Generate the survey JSON structure embedded into study metadata.

        Args:
            survey_id (int): Identifier of the survey to serialize.

        Returns:
            dict: Survey payload including questions, categories, and survey metadata.
        """
        logger.info("Survey.generate_json_for_study called for survey_id=%s", survey_id)
        survey_json = {}
        question_data = retrieve_all_questions_for_survey(survey_id)
        category_data = retrieve_all_categories_for_survey(survey_id)
        survey_json[constants.key_name_questions] = question_data
        survey_json[constants.key_name_categories] = category_data
        survey_details = retrieve_survey_details(survey_id)
        survey_json['id'] = survey_details['id']
        survey_json['title'] = survey_details['title']
        survey_json['description'] = survey_details['description']
        survey_json['topN'] = survey_details['topN']
        logger.info("Survey.generate_json_for_study finished for survey_id=%s", survey_id)
        logger.debug("Survey.generate_json_for_study return_value=%s", survey_json)
        return survey_json

    @staticmethod
    def create_answers(question_id, answers, question_type=None):
        """
        Create answer rows for a question.

        Args:
            question_id (int): Identifier of the parent question.
            answers (list): Normalized answer dictionaries to persist.
            question_type (int, optional): Question type used to derive sort order defaults.

        Returns:
            None
        """
        logger.info(
            "Survey.create_answers called for question_id=%s answer_count=%s question_type=%s",
            question_id,
            len(answers),
            question_type,
        )
        for index, answer in enumerate(answers):
            logger.info("Creating answer for question %s: %s", question_id, answer)
            answer['answerSortId'] = answer.get("answerSortId", index + 1 if question_type in [1, 2] else 1)
            create_answer_in_db(question_id, answer)
        logger.info("Survey.create_answers finished for question_id=%s", question_id)
        logger.debug("Survey.create_answers return_value=%s", None)

    @classmethod
    def create_question_with_answers(cls, survey_id, question_obj, answers):
        """
        Create a question and its answers for a survey.

        Args:
            survey_id (int): Identifier of the parent survey.
            question_obj (dict): Normalized question payload.
            answers (list): Normalized answer payload for the question.

        Returns:
            int: Identifier of the created question.
        """
        logger.info("Survey.create_question_with_answers called for survey_id=%s", survey_id)
        question_obj[constants.key_name_id] = question_obj[constants.key_name_sortId]
        question = create_question_answers_in_db(
            survey_id,
            normalize_question_data_defaults(question_obj),
        )

        if answers:
            cls.create_answers(question.pk, answers, question.questionType)

        logger.info("Survey.create_question_with_answers finished for survey_id=%s", survey_id)
        logger.debug("Survey.create_question_with_answers return_value=%s", question.pk)
        return question.pk

    @classmethod
    def update_question_with_answers(cls, question_id, question_obj, answers):
        """
        Update a question and replace its associated answers.

        Args:
            question_id (int): Identifier of the question to update.
            question_obj (dict): Normalized question payload.
            answers (list): Normalized answer payload to recreate for the question.

        Returns:
            int: Identifier of the parent survey.
        """
        logger.info("Survey.update_question_with_answers called for question_id=%s", question_id)
        question_obj = normalize_question_data_defaults(question_obj)
        question_type = int(question_obj["questionType"])

        with transaction.atomic():
            cls.update_question_order(question_id, question_obj["sortId"])
            update_question_in_db(question_id, question_obj)

            existing_answers = retrieve_all_answers_for_questions(question_id)
            for answer in existing_answers:
                delete_answer_in_db(answer["db_id"])
            if answers:
                cls.create_answers(question_id, answers, question_type)

        survey_id = retrieve_question(question_id).survey_id
        logger.info("Survey.update_question_with_answers finished for question_id=%s", question_id)
        logger.debug("Survey.update_question_with_answers return_value=%s", survey_id)
        return survey_id

    @classmethod
    def create_from_data(cls, form_data, user):
        """
        Create a survey from normalized survey form data.

        Args:
            form_data (dict): Normalized survey payload.
            user (User): User creating the survey.

        Returns:
            int: Identifier of the created survey.
        """
        logger.info("Survey.create_from_data called")
        survey = create_new_survey_in_db(form_data, user)
        logger.info("Survey.create_from_data finished")
        logger.debug("Survey.create_from_data return_value=%s", survey.id)
        return survey.id

    @classmethod
    def update_from_data(cls, form_data, survey_id):
        """
        Update survey metadata from normalized survey form data.

        Args:
            form_data (dict): Normalized survey payload.
            survey_id (int): Identifier of the survey to update.

        Returns:
            int: Identifier of the updated survey.
        """
        logger.info("Survey.update_from_data called for survey_id=%s", survey_id)
        survey = update_survey_info_in_db(form_data, survey_id)
        logger.info("Survey.update_from_data finished for survey_id=%s", survey_id)
        logger.debug("Survey.update_from_data return_value=%s", survey.id)
        return survey.id

    @classmethod
    def import_json_payload(cls, survey_str, user):
        """
        Import a survey from a JSON payload string.

        Args:
            survey_str (str): JSON string containing survey data.
            user (User): User performing the import.

        Returns:
            int: Identifier of the created survey.
        """
        logger.info("Survey.import_json_payload called")
        formatted_date = timezone.now().strftime("%Y-%m-%dT%H:%M:%S")
        survey_dict = {"survey": json.loads(survey_str)}
        survey_title = "survey_" + formatted_date
        survey = create_survey_in_db(survey_title, survey_dict["survey"], user)
        logger.info("Survey.import_json_payload finished")
        logger.debug("Survey.import_json_payload return_value=%s", survey.id)
        return survey.id

    @classmethod
    def import_file(cls, uploaded_file, user):
        """
        Import a survey from an uploaded file.

        This method accepts JSON, CSV, and Excel uploads. Non-JSON files are
        converted to survey JSON before creating the survey.

        Args:
            uploaded_file (UploadedFile): Uploaded survey file object.
            user (User): User performing the import.

        Returns:
            int: Identifier of the created survey.
        """
        logger.info("Survey.import_file called for filename=%s", uploaded_file.name)
        filename = uploaded_file.name.lower()

        if filename.endswith(".json"):
            survey_id = cls.import_json_payload(uploaded_file.read(), user)
            logger.info("Survey.import_file finished for filename=%s", filename)
            logger.debug("Survey.import_file return_value=%s", survey_id)
            return survey_id

        if filename.endswith((".xlsx", ".xls", ".xlsm", ".csv")):
            suffix = os.path.splitext(filename)[1]
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp_file:
                for chunk in uploaded_file.chunks():
                    tmp_file.write(chunk)
                tmp_file.flush()
                survey_json = SurveyFileToJSONConverter(tmp_file.name).to_json(pretty=False)
            survey_id = cls.import_json_payload(survey_json, user)
            logger.info("Survey.import_file finished for filename=%s", filename)
            logger.debug("Survey.import_file return_value=%s", survey_id)
            return survey_id

        raise ValueError("Unsupported survey upload format. Use JSON, CSV, XLSX, XLSM, or XLS.")

    @classmethod
    def delete_question(cls, question_id, survey_id):
        """
        Delete one question from a survey.

        Args:
            question_id (int): Identifier of the question to delete.
            survey_id (int): Identifier of the parent survey.

        Returns:
            int: Identifier of the parent survey.
        """
        logger.info("Survey.delete_question called for survey_id=%s question_id=%s", survey_id, question_id)
        survey_id = cls.delete_questions([question_id], survey_id)
        logger.info("Survey.delete_question finished for survey_id=%s question_id=%s", survey_id, question_id)
        logger.debug("Survey.delete_question return_value=%s", survey_id)
        return survey_id

    @staticmethod
    def _normalize_question_id(question_id):
        try:
            return int(question_id)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_condition_question_refs(value):
        if value in (None, "", []):
            return set()

        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                return set()
            try:
                parsed_value = json.loads(raw_value)
            except ValueError:
                parsed_value = raw_value.replace(";", ",").split(",")
            value = parsed_value

        if not isinstance(value, (list, tuple, set)):
            value = [value]

        question_refs = set()
        for item in value:
            normalized_id = Survey._normalize_question_id(item)
            if normalized_id is not None:
                question_refs.add(normalized_id)
        return question_refs

    @classmethod
    def _questions_selected_for_delete(cls, question_ids, all_questions):
        normalized_ids = []
        for question_id in question_ids:
            normalized_id = cls._normalize_question_id(question_id)
            if normalized_id is not None and normalized_id not in normalized_ids:
                normalized_ids.append(normalized_id)

        question_lookup = {
            cls._normalize_question_id(question.get("db_id")): question
            for question in all_questions
        }
        selected_questions = [
            question_lookup[question_id]
            for question_id in normalized_ids
            if question_id in question_lookup
        ]
        return sorted(
            selected_questions,
            key=lambda question: cls._normalize_question_id(question.get("sortId")) or 0,
            reverse=True,
        )

    @classmethod
    def _assert_questions_can_be_deleted(cls, selected_questions, all_questions):
        selected_db_ids = {
            cls._normalize_question_id(question.get("db_id"))
            for question in selected_questions
        }
        selected_sort_ids = {
            cls._normalize_question_id(question.get("sortId"))
            for question in selected_questions
        }
        selected_db_ids.discard(None)
        selected_sort_ids.discard(None)

        blockers = []
        for question in all_questions:
            question_db_id = cls._normalize_question_id(question.get("db_id"))
            if question_db_id in selected_db_ids:
                continue

            question_sort_id = cls._normalize_question_id(question.get("sortId"))
            for field_name in ("activate_question", "deactivate_question"):
                linked_sort_ids = cls._normalize_condition_question_refs(question.get(field_name))
                blocked_sort_ids = sorted(selected_sort_ids.intersection(linked_sort_ids))
                for blocked_sort_id in blocked_sort_ids:
                    blockers.append(
                        "Q%s %s -> Q%s" % (question_sort_id, field_name, blocked_sort_id)
                    )

        if blockers:
            raise ValueError(
                "Cannot delete selected questions. Remove condition links first: %s"
                % ", ".join(blockers)
            )

    @classmethod
    def _compact_question_order_after_delete(cls, survey_id, removed_sort_id):
        following_question_ids = list(
            Question.objects.filter(
                survey_id=survey_id,
                sortId__gt=removed_sort_id,
            ).order_by("sortId", "id").values_list("id", flat=True)
        )

        next_sort_id = removed_sort_id
        for following_question_id in following_question_ids:
            cls.update_question_order(following_question_id, next_sort_id)
            next_sort_id += 1

    @classmethod
    def _delete_question_without_dependency_check(cls, question_id, survey_id):
        question_id = cls._normalize_question_id(question_id)
        if question_id is None:
            return survey_id

        question = (
            Question.objects.select_for_update()
            .filter(id=question_id, survey_id=survey_id)
            .first()
        )
        if not question:
            return survey_id

        removed_sort_id = question.sortId
        deleted = delete_question_from_db(question_id, survey_id)
        if deleted:
            cls._compact_question_order_after_delete(survey_id, removed_sort_id)
        return survey_id

    @classmethod
    def delete_questions(cls, question_ids, survey_id):
        """
        Delete multiple questions from a survey and keep the remaining sort order compact.

        Args:
            question_ids (list): Question database IDs to delete.
            survey_id (int): Identifier of the parent survey.

        Returns:
            int: Identifier of the parent survey.
        """
        logger.info("Survey.delete_questions called for survey_id=%s question_ids=%s", survey_id, question_ids)
        all_questions = retrieve_all_questions_for_survey(survey_id)
        selected_questions = cls._questions_selected_for_delete(question_ids, all_questions)
        if not selected_questions:
            return survey_id

        cls._assert_questions_can_be_deleted(selected_questions, all_questions)

        with transaction.atomic():
            for question in selected_questions:
                cls._delete_question_without_dependency_check(question["db_id"], survey_id)
        return survey_id

    @staticmethod
    def update_question_order(question_id, new_sequence_id):
        """
        Reorder a question within its survey.

        Args:
            question_id (int): Identifier of the question being moved.
            new_sequence_id (int): Requested ``sortId`` for the question.

        Returns:
            None
        """
        logger.info(
            "Survey.update_question_order called for question_id=%s new_sequence_id=%s",
            question_id,
            new_sequence_id,
        )
        question = Question.objects.get(id=question_id)
        logger.info("update_sortid_of_questions %s :: %s", question, new_sequence_id)
        old_sequence_id = question.sortId

        if new_sequence_id > old_sequence_id:
            logger.info("Shifting questions down")
            questions_to_update = Question.objects.filter(
                survey=question.survey,
                sortId__gt=old_sequence_id,
                sortId__lte=new_sequence_id
            ).exclude(id=question_id).order_by('sortId')

            for q in questions_to_update:
                q.sortId -= 1
                logger.info("Shifted down question ID %s to sortId %d", q.id, q.sortId)
                q.save()

        elif new_sequence_id < old_sequence_id:
            logger.info("Shifting questions up")
            questions_to_update = Question.objects.filter(
                survey=question.survey,
                sortId__gte=new_sequence_id,
                sortId__lt=old_sequence_id
            ).exclude(id=question_id).order_by('-sortId')

            for q in questions_to_update:
                q.sortId += 1
                logger.info("Shifted up question ID %s to sortId %d", q.id, q.sortId)
                q.save()

        question.sortId = new_sequence_id
        question.save()
        logger.info("Updated moved question ID %s to new sortId: %d", question.id, new_sequence_id)
        logger.info("Survey.update_question_order finished for question_id=%s", question_id)
        logger.debug("Survey.update_question_order return_value=%s", True)
        return True

    @staticmethod
    def sync_categories(category_form_data, existing_categories, survey_id):
        """
        Synchronize survey categories against submitted category form data.

        Args:
            category_form_data (list): Normalized category payload from the formset.
            existing_categories (QuerySet): Existing category queryset for the survey.
            survey_id (int): Identifier of the parent survey.

        Returns:
            None
        """
        logger.info(
            "Survey.sync_categories called for survey_id=%s submitted_categories=%s existing_categories=%s",
            survey_id,
            len(category_form_data),
            existing_categories.count(),
        )
        category_data_dict = {
            data['categoryTitle']: {
                'categoryValue': data['categoryValue'],
                'didSubjectAsk': data['didSubjectAsk'],
            }
            for data in category_form_data
        }

        existing_category_names = set(existing_categories.values_list('categoryTitle', flat=True))
        form_category_names = set(category_data_dict.keys())

        categories_to_create = form_category_names - existing_category_names
        categories_to_update = form_category_names & existing_category_names
        categories_to_delete = existing_category_names - form_category_names

        with transaction.atomic():
            deleted_category_values = list(
                existing_categories.filter(categoryTitle__in=categories_to_delete)
                .values_list("categoryValue", flat=True)
            )

            for name in categories_to_create:
                category = Category(
                    categoryTitle=name,
                    categoryValue=category_data_dict[name]['categoryValue'],
                    didSubjectAsk=category_data_dict[name]['didSubjectAsk'],
                    survey_id=survey_id
                )
                category.save()

            for name in categories_to_update:
                category = existing_categories.get(categoryTitle=name)
                form_data = category_data_dict[name]
                if category.categoryValue != form_data['categoryValue'] or category.didSubjectAsk != form_data['didSubjectAsk']:
                    category.categoryValue = form_data['categoryValue']
                    category.didSubjectAsk = form_data['didSubjectAsk']
                    category.save()

            if categories_to_delete:
                Question.objects.filter(
                    survey_id=survey_id,
                    category__in=deleted_category_values,
                ).update(category=0)
                existing_categories.filter(categoryTitle__in=categories_to_delete).delete()
        logger.info("Survey.sync_categories finished for survey_id=%s", survey_id)
        logger.debug("Survey.sync_categories return_value=%s", None)

    @classmethod
    def update_categories(cls, survey_id, category_list, collect_flag):
        """
        Update survey categories and apply the collect-subject flag.

        Args:
            survey_id (int): Identifier of the survey whose categories are updated.
            category_list (list): Normalized category payload.
            collect_flag (bool): Value to apply to ``didSubjectAsk`` on each category.

        Returns:
            None
        """
        logger.info(
            "Survey.update_categories called for survey_id=%s category_count=%s collect_flag=%s",
            survey_id,
            len(category_list),
            collect_flag,
        )
        for category in category_list:
            category["didSubjectAsk"] = collect_flag

        existing_categories = get_categories_from_db(survey_id)
        cls.sync_categories(category_list, existing_categories, survey_id)
        logger.info("Survey.update_categories finished for survey_id=%s", survey_id)
        logger.debug("Survey.update_categories return_value=%s", None)


def update_survey_details(study_name, values_obj, is_question):
    """
    Update the embedded legacy survey section inside a study JSON file.

    Args:
        study_name (str): Name of the study JSON file to update.
        values_obj (dict): Updated values to write into the embedded survey payload.
        is_question (bool): Whether the update targets a question or survey-level data.

    Returns:
        dict: Updated study JSON payload.
    """
    logger.info(
        "update_survey_details called for study_name=%s is_question=%s keys=%s",
        study_name,
        is_question,
        list(values_obj.keys()),
    )
    study_json = open_study_json(study_name)
    if is_question:
        question_id = values_obj['id']
        for question in study_json['survey']['questions']:
            if question['id'] == int(question_id):
                question['title'] = values_obj['title']
                question['subText'] = values_obj['subText']
                question['frequency'] = values_obj['frequency']
                question['clockTime'] = values_obj['clockTime']
                question['nextDayToAnswer'] = values_obj['nextDayToAnswer']
                question['category'] = values_obj['category']
                question['imageURL'] = values_obj['imageURL']
                question['url'] = values_obj['url']
                question['questionType'] = values_obj['questionType']
                question['mandatory'] = coerce_bool(values_obj.get('mandatory'), default=False)
                question['deactivateOnAnswer'] = values_obj['deactivateOnAnswer']
                question['deactivateOnDate'] = values_obj['deactivateOnDate']
    else:
        study_json['survey']['title'] = values_obj['title']
        study_json['survey']['description'] = values_obj['description']
        study_json['splitbyCategory'] = values_obj['splitbyCategory']
        study_json['scrolling'] = values_obj['scrolling']
        study_json['survey']['topN'] = values_obj['topN']
    save_study_json(study_name, study_json)
    logger.info("update_survey_details finished for study_name=%s", study_name)
    logger.debug("update_survey_details return_value=%s", True)
    return True

