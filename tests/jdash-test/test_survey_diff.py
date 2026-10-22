from jdash.services.survey_diff import build_survey_change_summary


def test_survey_diff_reports_content_and_order_changes():
    committed = {
        "title": "Mood",
        "description": "Old description",
        "topN": -1,
        "splitbyCategory": False,
        "scrolling": "V",
        "categories": [
            {"categoryValue": 1, "categoryTitle": "Mood"},
            {"categoryValue": 2, "categoryTitle": "Sleep"},
        ],
        "questions": [
            {"db_id": 10, "id": 1, "title": "Old title", "answer": []},
            {"db_id": 20, "id": 2, "title": "Unchanged", "answer": []},
            {"db_id": 30, "id": 3, "title": "Deleted", "answer": []},
        ],
    }
    current = {
        "title": "Mood",
        "description": "New description",
        "topN": -1,
        "splitbyCategory": False,
        "scrolling": "V",
        "categories": [
            {"categoryValue": 1, "categoryTitle": "Wellbeing"},
            {"categoryValue": 3, "categoryTitle": "Activity"},
        ],
        "questions": [
            {"db_id": 20, "id": 1, "title": "Unchanged", "answer": []},
            {"db_id": 10, "id": 2, "title": "New title", "answer": []},
            {"db_id": 40, "id": 3, "title": "Added", "answer": []},
        ],
    }

    result = build_survey_change_summary(current, committed)

    assert result == {
        "never_committed": False,
        "question_count": 3,
        "category_count": 2,
        "survey_details_changed": True,
        "questions_added": 1,
        "questions_updated": 1,
        "questions_deleted": 1,
        "questions_reordered": True,
        "categories_added": 1,
        "categories_updated": 1,
        "categories_deleted": 1,
        "has_changes": True,
    }


def test_survey_diff_reports_full_content_when_never_committed():
    result = build_survey_change_summary(
        {"questions": [{"db_id": 1}], "categories": [{"categoryValue": 1}]},
        None,
    )

    assert result["never_committed"] is True
    assert result["question_count"] == 1
    assert result["category_count"] == 1
    assert result["has_changes"] is True


def test_survey_diff_ignores_question_display_order_during_content_comparison():
    committed = {
        "questions": [
            {"db_id": 1, "id": 1, "title": "One"},
            {"db_id": 2, "id": 2, "title": "Two"},
        ],
        "categories": [],
    }
    current = {
        "questions": [
            {"db_id": 2, "id": 1, "title": "Two"},
            {"db_id": 1, "id": 2, "title": "One"},
        ],
        "categories": [],
    }

    result = build_survey_change_summary(current, committed)

    assert result["questions_updated"] == 0
    assert result["questions_reordered"] is True
