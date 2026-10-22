import copy
import json
import os
import re
from datetime import datetime

from jdash.config import constants as constants
from jdash.config import runtime_config as config
from jdash.utils.fileutils import (
    _load_json_file,
    _next_study_json_version,
    _normalize_study_json_for_context,
    _study_json_path,
    create_backup_json_file,
    open_study_json,
    save_study_json,
    save_study_json_with_version_backup,
)


def _legacy_survey_draft_path(study_name):
    return os.path.join(config.studies_folder, study_name, study_name + '_survey_draft.json')


def legacy_survey_draft_exists(study_name):
    return os.path.isfile(_legacy_survey_draft_path(study_name))


def discard_legacy_survey_draft(study_name):
    path = _legacy_survey_draft_path(study_name)
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def get_legacy_survey_edit_json(study_name):
    path = _legacy_survey_draft_path(study_name)
    if not os.path.isfile(path):
        path = _study_json_path(study_name)
    return _normalize_study_json_for_context(_load_json_file(path))


def get_legacy_survey_edit_updated_at(study_name):
    path = _legacy_survey_draft_path(study_name)
    if not os.path.isfile(path):
        path = _study_json_path(study_name)
    try:
        return datetime.fromtimestamp(os.path.getmtime(path))
    except OSError:
        return None


def save_legacy_survey_draft_json(study_name, study_json):
    if not isinstance(study_json, dict):
        raise ValueError(f"Invalid survey draft JSON for {study_name}: not a dict")

    required_keys = [constants.key_study_name_json, constants.key_name_survey]
    missing = [key for key in required_keys if key not in study_json]

    if missing:
        raise ValueError(
            f"Refusing to write {study_name} survey draft: missing keys {missing}. "
            f"Got keys: {list(study_json.keys())}"
        )

    with open(_legacy_survey_draft_path(study_name), 'w', encoding=constants.encoding) as jf:
        json.dump(study_json, jf, ensure_ascii=False, indent=4)


def open_legacy_survey_edit_json(study_name, create_draft=False):
    draft_path = _legacy_survey_draft_path(study_name)
    if os.path.isfile(draft_path):
        return _load_json_file(draft_path)

    study_json = open_study_json(study_name)
    if create_draft:
        save_legacy_survey_draft_json(study_name, study_json)
    return study_json


def _legacy_survey_questions(study_json):
    survey = study_json.setdefault(constants.key_name_survey, {})
    questions = survey.setdefault(constants.key_name_questions, [])
    if not isinstance(questions, list):
        raise ValueError("Study survey questions must be a list.")
    return questions


def _legacy_question_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_legacy_question_flags(question):
    if constants.field_name_active in question:
        question[constants.field_name_active] = 1
    if constants.field_name_mandatory in question:
        question[constants.field_name_mandatory] = 0
    return question


def _remap_legacy_question_refs(value, id_map):
    if value in (None, "", [], {}):
        return value

    question_ids = _legacy_question_ids_from_value(value)
    if not question_ids:
        return value

    remapped_ids = [id_map.get(question_id, question_id) for question_id in question_ids]
    if isinstance(value, tuple):
        return tuple(remapped_ids)
    if isinstance(value, set):
        return set(remapped_ids)
    if isinstance(value, str):
        raw_value = value.strip()
        if raw_value.startswith("["):
            return json.dumps(remapped_ids)
        if ";" in raw_value:
            return ";".join(str(question_id) for question_id in remapped_ids)
        if "," in raw_value:
            return ",".join(str(question_id) for question_id in remapped_ids)
        return str(remapped_ids[0]) if len(remapped_ids) == 1 else ",".join(
            str(question_id) for question_id in remapped_ids
        )
    return remapped_ids


def _find_legacy_question_index(questions, question_id=None, title=None):
    normalized_id = _legacy_question_id(question_id)
    if normalized_id is not None:
        for index, question in enumerate(questions):
            if _legacy_question_id(question.get(constants.key_name_id)) == normalized_id:
                return index

    if title:
        for index, question in enumerate(questions):
            if question.get(constants.field_name_title) == title:
                return index

    raise ValueError("Question was not found in the study survey file.")


def _next_legacy_question_id(questions):
    existing_ids = [
        _legacy_question_id(question.get(constants.key_name_id))
        for question in questions
    ]
    existing_ids = [question_id for question_id in existing_ids if question_id is not None]
    return max(existing_ids, default=0) + 1


def _split_legacy_choice_text(value):
    return [
        choice.strip()
        for choice in str(value or "").split(";")
        if choice.strip()
    ]


def _legacy_question_ids_from_value(value):
    if value in (None, "", [], {}):
        return []
    if isinstance(value, (list, tuple, set)):
        return [
            question_id
            for question_id in (_legacy_question_id(item) for item in value)
            if question_id is not None
        ]
    if isinstance(value, int):
        return [value]

    raw_value = str(value).strip()
    if not raw_value or raw_value.lower() in ("[]", "none", "null"):
        return []

    try:
        parsed_value = json.loads(raw_value.replace("'", '"'))
        if isinstance(parsed_value, list):
            return _legacy_question_ids_from_value(parsed_value)
    except (TypeError, ValueError):
        pass

    return [
        question_id
        for question_id in (
            _legacy_question_id(item.strip().strip('"').strip("'"))
            for item in re.split(r"[,;]", raw_value.strip("[]"))
        )
        if question_id is not None
    ]


def _normalize_legacy_answer_keys(answer):
    if not isinstance(answer, dict):
        return answer

    if constants.field_name_minVal not in answer and constants.field_name_minValue in answer:
        answer[constants.field_name_minVal] = answer[constants.field_name_minValue]
    if constants.field_name_maxVal not in answer and constants.field_name_maxValue in answer:
        answer[constants.field_name_maxVal] = answer[constants.field_name_maxValue]
    answer.pop(constants.field_name_minValue, None)
    answer.pop(constants.field_name_maxValue, None)
    return answer


def _build_legacy_answers(question_type, answer_data, existing_answers=None):
    existing_answers = list(existing_answers or [])
    answer_data = answer_data or {}
    question_type = _legacy_question_id(question_type)

    if question_type in (1, 2):
        choices = _split_legacy_choice_text(answer_data.get(constants.field_name_text))
        if not choices:
            return existing_answers

        answers = []
        for index, choice in enumerate(choices):
            answer = copy.deepcopy(existing_answers[index]) if index < len(existing_answers) else {}
            answer[constants.key_name_id] = answer.get(constants.key_name_id, index + 1)
            answer[constants.field_name_text] = choice
            answer.setdefault(constants.field_name_value, index + 1)
            answers.append(_normalize_legacy_answer_keys(answer))
        return answers

    answer = copy.deepcopy(existing_answers[0]) if existing_answers else {}
    answer[constants.key_name_id] = answer.get(constants.key_name_id, 1)
    answer[constants.field_name_text] = (
        answer_data.get(constants.field_name_text)
        or answer.get(constants.field_name_text, "N")
    )
    for key in (
        constants.field_name_answerSubText,
        constants.field_name_value,
        constants.field_name_defaultValue,
        constants.field_name_stepSize,
        constants.field_name_minText,
        constants.field_name_maxText,
        constants.field_name_answerSortId,
    ):
        value = answer_data.get(key)
        if value not in (None, ""):
            answer[key] = value
    min_value = answer_data.get(
        constants.field_name_minVal,
        answer_data.get(constants.field_name_minValue),
    )
    if min_value not in (None, ""):
        answer[constants.field_name_minVal] = min_value
    max_value = answer_data.get(
        constants.field_name_maxVal,
        answer_data.get(constants.field_name_maxValue),
    )
    if max_value not in (None, ""):
        answer[constants.field_name_maxVal] = max_value
    _normalize_legacy_answer_keys(answer)
    return [answer]


def update_legacy_survey_question(study_name, question_data, answer_data=None):
    study_json = open_legacy_survey_edit_json(study_name, create_draft=True)
    questions = _legacy_survey_questions(study_json)
    question_index = _find_legacy_question_index(
        questions,
        question_id=question_data.get(constants.key_name_id),
    )
    question = questions[question_index]

    for key, value in question_data.items():
        if key == constants.key_name_id:
            continue
        if key == constants.field_name_active:
            question[key] = 1
            continue
        if key == constants.field_name_mandatory:
            question[key] = 0
            continue
        if value is not None:
            question[key] = value

    question[constants.key_name_id] = (
        _legacy_question_id(question_data.get(constants.key_name_id))
        or question.get(constants.key_name_id)
    )
    question[constants.field_name_answer] = _build_legacy_answers(
        question.get(constants.field_name_questionType),
        answer_data,
        question.get(constants.field_name_answer, []),
    )
    _normalize_legacy_question_flags(question)

    save_legacy_survey_draft_json(study_name, study_json)
    return study_json


def update_legacy_survey_question_order(study_name, question_id, new_sort_id):
    study_json = open_legacy_survey_edit_json(study_name, create_draft=True)
    questions = _legacy_survey_questions(study_json)
    new_sort_id = _legacy_question_id(new_sort_id)

    if not questions:
        return study_json
    if new_sort_id is None or new_sort_id < 1 or new_sort_id > len(questions):
        raise ValueError(f"Question order must be between 1 and {len(questions)}.")

    current_index = _find_legacy_question_index(questions, question_id=question_id)
    question = questions.pop(current_index)
    questions.insert(new_sort_id - 1, question)

    ordered_questions = [
        (question, _legacy_question_id(question.get(constants.key_name_id)) or index)
        for index, question in enumerate(questions, start=1)
    ]
    id_map = {
        old_id: index
        for index, (question, old_id) in enumerate(ordered_questions, start=1)
    }

    for index, (question, old_id) in enumerate(ordered_questions, start=1):
        question[constants.key_name_id] = index
        for field_name in (constants.field_name_activate_question, constants.field_name_deactivate_question):
            if field_name in question:
                question[field_name] = _remap_legacy_question_refs(
                    question.get(field_name),
                    id_map,
                )
        _normalize_legacy_question_flags(question)

    save_legacy_survey_draft_json(study_name, study_json)
    return study_json


def delete_legacy_survey_question(study_name, question_id=None, title=None):
    return delete_legacy_survey_questions(study_name, question_ids=[question_id], title=title)


def delete_legacy_survey_questions(study_name, question_ids=None, title=None):
    study_json = open_legacy_survey_edit_json(study_name, create_draft=True)
    questions = _legacy_survey_questions(study_json)

    selected_ids = {
        question_id
        for question_id in (_legacy_question_id(value) for value in (question_ids or []))
        if question_id is not None
    }

    if not selected_ids and title:
        selected_ids.add(
            _legacy_question_id(
                questions[_find_legacy_question_index(questions, title=title)].get(constants.key_name_id)
            )
        )

    if not selected_ids:
        return study_json

    linked_questions = []
    for question in questions:
        current_id = _legacy_question_id(question.get(constants.key_name_id))
        if current_id in selected_ids:
            continue

        linked_ids = set(_legacy_question_ids_from_value(question.get(constants.field_name_activate_question)))
        linked_ids.update(_legacy_question_ids_from_value(question.get(constants.field_name_deactivate_question)))
        if linked_ids.intersection(selected_ids):
            linked_questions.append(current_id)

    if linked_questions:
        raise ValueError(
            "Cannot delete selected question(s) because they are used in "
            f"activation/deactivation conditions by question(s): {', '.join(map(str, linked_questions))}."
        )

    questions[:] = [
        question
        for question in questions
        if _legacy_question_id(question.get(constants.key_name_id)) not in selected_ids
    ]
    save_legacy_survey_draft_json(study_name, study_json)
    return study_json


def update_legacy_survey_categories(study_name, category_list, collect_flag=False):
    study_json = open_legacy_survey_edit_json(study_name, create_draft=True)
    survey = study_json.setdefault(constants.key_name_survey, {})
    questions = _legacy_survey_questions(study_json)
    existing_categories = survey.get(constants.key_name_categories, []) or []
    existing_values = {
        _legacy_question_id(category.get(constants.key_name_categoryValue))
        for category in existing_categories
        if isinstance(category, dict)
    }
    existing_values.discard(None)

    updated_categories = []
    for index, category in enumerate(category_list or [], start=1):
        title = str(category.get(constants.key_name_categoryTitle, "")).strip()
        if not title:
            continue

        category_value = _legacy_question_id(category.get(constants.key_name_categoryValue)) or index
        updated_categories.append(
            {
                constants.key_name_categoryTitle: title,
                constants.key_name_categoryValue: category_value,
                constants.key_name_didSubjectAsk: bool(collect_flag),
            }
        )

    updated_values = {
        _legacy_question_id(category.get(constants.key_name_categoryValue))
        for category in updated_categories
    }
    updated_values.discard(None)
    deleted_values = existing_values - updated_values

    if deleted_values:
        for question in questions:
            if _legacy_question_id(question.get(constants.field_name_category)) in deleted_values:
                question[constants.field_name_category] = 0

    survey[constants.key_name_categories] = updated_categories
    save_legacy_survey_draft_json(study_name, study_json)
    return study_json


def duplicate_legacy_survey_question(study_name, question_id):
    study_json = open_legacy_survey_edit_json(study_name, create_draft=True)
    questions = _legacy_survey_questions(study_json)
    question_index = _find_legacy_question_index(questions, question_id=question_id)
    duplicated_question = copy.deepcopy(questions[question_index])
    duplicated_question.pop(constants.field_name_db_id, None)
    duplicated_question[constants.key_name_id] = _next_legacy_question_id(questions)
    _normalize_legacy_question_flags(duplicated_question)
    for answer in duplicated_question.get(constants.field_name_answer, []):
        if isinstance(answer, dict):
            answer.pop(constants.field_name_db_id, None)
            _normalize_legacy_answer_keys(answer)
    questions.append(duplicated_question)
    save_legacy_survey_draft_json(study_name, study_json)
    return study_json


def publish_legacy_survey(study_name):
    if not legacy_survey_draft_exists(study_name):
        return open_study_json(study_name), False

    study_json = open_study_json(study_name)
    draft_json = open_legacy_survey_edit_json(study_name)
    draft_survey = draft_json.get(constants.key_name_survey)
    if not draft_survey:
        raise ValueError("No file-based survey found to publish.")

    published_json = copy.deepcopy(study_json)
    published_json[constants.key_name_survey] = draft_survey
    create_backup_json_file(study_name, copy.deepcopy(study_json))
    published_json[constants.key_name_version] = _next_study_json_version(study_json)
    save_study_json(study_name, published_json)
    discard_legacy_survey_draft(study_name)
    return published_json, True


def delete_legacy_survey(study_name):
    study_json = open_study_json(study_name)
    study_json[constants.key_name_survey] = {}
    save_study_json_with_version_backup(study_name, study_json)
    return study_json

