"""Compare the editable DB survey with a study's committed survey snapshot."""

from copy import deepcopy


SURVEY_DETAIL_FIELDS = (
    "title",
    "description",
    "topN",
    "splitbyCategory",
    "scrolling",
)


def _question_key(question):
    value = question.get("db_id")
    if value in (None, ""):
        value = question.get("id")
    return "" if value in (None, "") else str(value)


def _category_key(category):
    value = category.get("categoryValue")
    if value in (None, ""):
        value = category.get("id")
    return "" if value in (None, "") else str(value)


def _without_keys(value, keys):
    normalized = deepcopy(value)
    for key in keys:
        normalized.pop(key, None)
    return normalized


def _index_by(items, key_function):
    return {
        key: item
        for item in items or []
        if (key := key_function(item))
    }


def build_survey_change_summary(current_survey, committed_survey):
    """Return structured changes between current and committed survey JSON."""
    current_survey = current_survey or {}
    committed_survey = committed_survey or {}

    current_questions = current_survey.get("questions") or []
    current_categories = current_survey.get("categories") or []

    if not committed_survey:
        return {
            "never_committed": True,
            "question_count": len(current_questions),
            "category_count": len(current_categories),
            "survey_details_changed": False,
            "questions_added": 0,
            "questions_updated": 0,
            "questions_deleted": 0,
            "questions_reordered": False,
            "categories_added": 0,
            "categories_updated": 0,
            "categories_deleted": 0,
            "has_changes": True,
        }

    committed_questions = committed_survey.get("questions") or []
    committed_categories = committed_survey.get("categories") or []
    current_question_map = _index_by(current_questions, _question_key)
    committed_question_map = _index_by(committed_questions, _question_key)
    current_category_map = _index_by(current_categories, _category_key)
    committed_category_map = _index_by(committed_categories, _category_key)

    shared_question_ids = current_question_map.keys() & committed_question_map.keys()
    shared_category_ids = current_category_map.keys() & committed_category_map.keys()

    questions_updated = sum(
        _without_keys(current_question_map[key], {"id", "db_id"})
        != _without_keys(committed_question_map[key], {"id", "db_id"})
        for key in shared_question_ids
    )
    categories_updated = sum(
        _without_keys(current_category_map[key], {"id"})
        != _without_keys(committed_category_map[key], {"id"})
        for key in shared_category_ids
    )

    current_order = [_question_key(question) for question in current_questions]
    committed_order = [_question_key(question) for question in committed_questions]
    shared_ids = set(shared_question_ids)
    questions_reordered = (
        [key for key in current_order if key in shared_ids]
        != [key for key in committed_order if key in shared_ids]
    )

    summary = {
        "never_committed": False,
        "question_count": len(current_questions),
        "category_count": len(current_categories),
        "survey_details_changed": any(
            current_survey.get(field) != committed_survey.get(field)
            for field in SURVEY_DETAIL_FIELDS
        ),
        "questions_added": len(current_question_map.keys() - committed_question_map.keys()),
        "questions_updated": questions_updated,
        "questions_deleted": len(committed_question_map.keys() - current_question_map.keys()),
        "questions_reordered": questions_reordered,
        "categories_added": len(current_category_map.keys() - committed_category_map.keys()),
        "categories_updated": categories_updated,
        "categories_deleted": len(committed_category_map.keys() - current_category_map.keys()),
    }
    summary["has_changes"] = any(
        value
        for key, value in summary.items()
        if key not in {"never_committed", "question_count", "category_count"}
    )
    return summary
