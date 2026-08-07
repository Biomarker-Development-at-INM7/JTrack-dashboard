import pytest
from contextlib import nullcontext
from unittest.mock import MagicMock, patch
from jdash.services import survey
from jdash.models import Category
from jdash.config import constants


@pytest.fixture
def sample_survey_json():
    """Fixture returning a sample survey JSON dictionary for testing."""
    return {
        'id': 1,
        'title': 'Sample Survey',
        'description': 'A sample survey description',
        'splitbyCategory': True,
        'scrolling': False,
        'topN': 5,
        'questions': [
            {
                'id': 101,
                'title': 'Question 1',
                'questionType': 'multiple-choice',
                'subText': 'Sub text',
                'category': 'cat1',
                'frequency': 1,
                'clockTime': '08:00',
                'nextDayToAnswer': 1,
                'imageURL': '',
                'url': '',
                'deactivateOnAnswer': False,
                'deactivateOnDate': None,
                'answers': [
                    {
                        'id': 1001,
                        'answerText': 'Answer 1',
                        'answerValue': 1,
                        'defaultValue': True,
                        'stepSize': None,
                        'minValue': None,
                        'maxValue': None,
                        'minText': None,
                        'maxText': None,
                    }
                ]
            }
        ]
    }


def test_survey_add_and_update_question_and_answer(sample_survey_json):
    """
    Test adding questions and answers, and updating their properties.
    Ensures data structures update correctly and warning logic on missing IDs.
    """
    s = survey.Survey(
        sample_survey_json['id'],
        sample_survey_json['title'],
        sample_survey_json['description'],
        sample_survey_json['splitbyCategory'],
        sample_survey_json['scrolling'],
        sample_survey_json['topN']
    )

    question = sample_survey_json['questions'][0]
    s.add_question(question)

    assert question['id'] in s.questions
    assert s.questions[question['id']]['title'] == question['title']

    # Add answer to question and verify addition
    answer = question['answers'][0]
    s.add_answer_to_question(question['id'], answer)
    assert answer['id'] in s.questions[question['id']]['answers']

    # Update question details and verify
    updated_question_data = {'title': 'Updated Question', 'category': 'cat2'}
    s.update_question(question['id'], updated_question_data)
    assert s.questions[question['id']]['title'] == 'Updated Question'
    assert s.questions[question['id']]['category'] == 'cat2'

    # Update answer details and verify
    updated_answer_data = {'id': answer['id'], 'answerText': 'Updated Answer'}
    s.update_answer(question['id'], updated_answer_data)
    assert s.questions[question['id']]['answers'][answer['id']]['answerText'] == 'Updated Answer'


def test_to_json_and_from_json(sample_survey_json):
    """
    Test serialization to JSON and deserialization from JSON.
    Validates structural integrity of the Survey object through these operations.
    """
    s = survey.Survey.from_json(sample_survey_json)
    json_data = s.to_json()
    assert json_data['id'] == sample_survey_json['id']
    assert json_data['title'] == sample_survey_json['title']
    assert isinstance(json_data['questions'], list)
    assert len(json_data['questions']) == len(sample_survey_json['questions'])


@patch('jdash.services.survey.retrieve_download_questions_for_survey')
@patch('jdash.services.survey.retrieve_all_categories_for_survey')
@patch('jdash.services.survey.retrieve_survey_details')
def test_generate_survey_json_for_download(mock_retrieve_details, mock_retrieve_categories, mock_retrieve_questions):
    """
    Test that survey JSON generation correctly combines questions, categories, and survey details.
    Uses mocked DB retrieval functions.
    """
    mock_retrieve_questions.return_value = ['q1', 'q2']
    mock_retrieve_categories.return_value = ['cat1', 'cat2']
    mock_retrieve_details.return_value = {
        'id': 1,
        'title': 'Survey Title',
        'description': 'Survey Desc',
        'topN': 10,
        'splitbyCategory': True,
        'scrolling': False,
    }

    result = survey.generate_survey_json_for_download(1)
    assert result['id'] == 1
    assert 'questions' in result
    assert 'categories' in result
    assert result['topN'] == 10
    assert result['splitbyCategory'] is True


@patch('jdash.services.survey.create_answer_in_db')
def test_check_and_enter_answer_in_db(mock_create_answer):
    """
    Test that answers from form data are correctly inserted into the database.
    """
    question_id = 123
    form_data = [{'id': 1, 'answerText': 'A1'}, {'id': 2, 'answerText': 'A2'}]
    survey.check_and_enter_answer_in_db(question_id, form_data)
    assert mock_create_answer.call_count == 2


@patch('jdash.services.survey.update_answer_in_db')
@patch('jdash.services.survey.delete_answer_in_db')
@patch('jdash.services.survey.create_answer_in_db')
def test_update_answer_choice_text_details(mock_create, mock_delete, mock_update):
    """
    Test updating existing answers, deleting removed ones, and creating new answers.
    """

    question_id = 1

    # Case 1: form_data length equals existing_ids (update all)
    existing_ids = [1, 2]
    form_data = [
        {'id': 1, 'answerText': 'Updated A1'},
        {'id': 2, 'answerText': 'Updated A2'},
    ]
    survey.update_answer_choice_text_details(question_id, form_data, existing_ids)
    mock_update.assert_called()
    mock_delete.assert_not_called()
    mock_create.assert_not_called()

    mock_update.reset_mock()
    mock_delete.reset_mock()
    mock_create.reset_mock()

    # Case 2: form_data length less than existing_ids (delete one)
    existing_ids = [1, 2, 3]
    form_data = [
        {'id': 1, 'answerText': 'Updated A1'},
        {'id': 2, 'answerText': 'Updated A2'},
    ]
    survey.update_answer_choice_text_details(question_id, form_data, existing_ids)
    mock_update.assert_not_called()
    mock_delete.assert_called()
    mock_create.assert_not_called()

    mock_update.reset_mock()
    mock_delete.reset_mock()
    mock_create.reset_mock()

    # Case 3: form_data length greater than existing_ids (create new)
    existing_ids = [1, 2]
    form_data = [
        {'id': 1, 'answerText': 'Updated A1'},
        {'id': 2, 'answerText': 'Updated A2'},
        {'id': 3, 'answerText': 'New Answer'},
    ]
    survey.update_answer_choice_text_details(question_id, form_data, existing_ids)
    mock_update.assert_not_called()
    mock_delete.assert_not_called()
    mock_create.assert_called()


@patch('jdash.services.survey.update_answer_in_db')
def test_update_other_answer_details(mock_update):
    """
    Test updating 'other' type answer details for a question.
    """
    question_id = 1
    form_data = [{'id': 10, 'answerText': 'Other A1'}]
    answer_id_list = [10]

    survey.update_other_answer_details(question_id, form_data, answer_id_list)
    mock_update.assert_called_once()


@patch('jdash.services.survey.Question.objects.get')
@patch('jdash.services.survey.Question.objects.filter')
def test_update_sortid_of_questions(mock_filter, mock_get):
    """
    Test that questions are correctly reordered when sortId is updated.
    Mocks Django ORM querysets and verifies correct method calls.
    """
    question_mock = MagicMock()
    question_mock.id = 1
    question_mock.sortId = 3
    question_mock.survey = MagicMock()

    mock_get.return_value = question_mock

    # Setup mock filter returns a list of questions
    qs_mock = MagicMock()
    qs_mock.exclude.return_value.order_by.return_value = [MagicMock(sortId=4), MagicMock(sortId=5)]
    mock_filter.return_value = qs_mock

    result = survey.update_sortid_of_questions(1, 5)
    assert result is True
    mock_get.assert_called_once()
    mock_filter.assert_called()


def test_delete_questions_deletes_selected_questions_highest_sort_first(monkeypatch):
    questions = [
        {"db_id": 10, "sortId": 1, "activate_question": [], "deactivate_question": []},
        {"db_id": 20, "sortId": 2, "activate_question": [], "deactivate_question": []},
        {"db_id": 30, "sortId": 3, "activate_question": [], "deactivate_question": []},
        {"db_id": 40, "sortId": 4, "activate_question": [], "deactivate_question": []},
    ]
    deleted_questions = []

    monkeypatch.setattr(survey, "retrieve_all_questions_for_survey", lambda survey_id: questions)
    monkeypatch.setattr(survey.transaction, "atomic", lambda: nullcontext())

    def fake_delete_question(cls, question_id, survey_id):
        deleted_questions.append((question_id, survey_id))

    monkeypatch.setattr(
        survey.Survey,
        "_delete_question_without_dependency_check",
        classmethod(fake_delete_question),
    )

    result = survey.Survey.delete_questions(["20", "40", "not-an-id"], 123)

    assert result == 123
    assert deleted_questions == [(40, 123), (20, 123)]


def test_delete_questions_blocks_questions_used_by_conditions(monkeypatch):
    questions = [
        {"db_id": 10, "sortId": 1, "activate_question": [], "deactivate_question": []},
        {"db_id": 20, "sortId": 2, "activate_question": [], "deactivate_question": []},
        {"db_id": 30, "sortId": 3, "activate_question": [2], "deactivate_question": []},
    ]

    monkeypatch.setattr(survey, "retrieve_all_questions_for_survey", lambda survey_id: questions)

    with pytest.raises(ValueError, match="Q3 activate_question -> Q2"):
        survey.Survey.delete_questions(["20"], 123)


@patch('django.db.transaction.atomic')
@patch('jdash.models.Category.objects.bulk_create')
@patch('jdash.models.Category.objects.filter')
def test_process_category_data(mock_filter, mock_bulk_create, mock_atomic):
    """
    Test processing category data: creating new categories,
    updating existing ones, and deleting removed categories.
    """
    survey_id = 1
    category_form_data = [
        {'categoryTitle': 'Cat1', 'categoryValue': 'Val1', 'didSubjectAsk': True},
        {'categoryTitle': 'Cat2', 'categoryValue': 'Val2', 'didSubjectAsk': False},
    ]

    existing_cat1 = MagicMock(categoryTitle='Cat1', categoryValue='OldVal', didSubjectAsk=False)
    existing_cat2 = MagicMock(categoryTitle='Cat3', categoryValue='Val3', didSubjectAsk=True)

    existing_categories = MagicMock()
    existing_categories.values_list.return_value = ['Cat1', 'Cat3']
    existing_categories.get.side_effect = lambda categoryTitle: existing_cat1 if categoryTitle == 'Cat1' else existing_cat2
    existing_categories.filter.return_value.delete.return_value = None

    survey.process_category_data(category_form_data, existing_categories, survey_id)

    mock_bulk_create.assert_called_once()  # Should create 'Cat2'
    existing_cat1.save.assert_called_once()  # Should update 'Cat1'
    existing_categories.filter.assert_called_once()  # Should delete 'Cat3'
    mock_atomic.assert_called_once()


@pytest.fixture
def category_instance_factory():
    def _factory(categoryTitle, categoryValue, didSubjectAsk, survey_id):
        inst = MagicMock(spec=Category)
        inst.categoryTitle = categoryTitle
        inst.categoryValue = categoryValue
        inst.didSubjectAsk = didSubjectAsk
        inst.survey_id = survey_id
        return inst
    return _factory


@pytest.mark.django_db
@patch('jdash.services.survey.transaction.atomic')
@patch('jdash.services.survey.Category.objects')
def test_process_incategory_data_creates_updates_deletes(mock_category_objects, mock_atomic, category_instance_factory):
    # Prepare mock queryset for existing categories
    existing_categories_dict = {
        'CatA': {'id': 1, 'value': 'ValA', 'didSubjectAsk': True},
        'CatB': {'id': 2, 'value': 'ValB', 'didSubjectAsk': False},
        'CatC': {'id': 3, 'value': 'ValC', 'didSubjectAsk': True},
    }

    # Create a consistent mock queryset to return from exclude()
    mock_exclude_qs = MagicMock()
    mock_exclude_qs.exists.return_value = True
    mock_exclude_qs.delete.return_value = None

    # Setup exclude side effect to return the consistent mock queryset
    def exclude_side_effect(**kwargs):
        cats_in_form = kwargs.get('categoryTitle__in', [])
        if 'CatC' not in cats_in_form:
            return mock_exclude_qs
        else:
            empty_qs = MagicMock()
            empty_qs.exists.return_value = False
            empty_qs.delete.return_value = None
            return empty_qs

    existing_categories = MagicMock()
    existing_categories.exclude.side_effect = exclude_side_effect

    # Setup __contains__ and __getitem__ for dict-like behavior
    existing_categories.__contains__.side_effect = lambda x: x in existing_categories_dict
    existing_categories.__getitem__.side_effect = lambda key: existing_categories_dict[key]

    # Patch filter().update()
    filter_mock = MagicMock()
    mock_category_objects.filter.return_value = filter_mock
    filter_mock.update.return_value = None

    # Patch bulk_create
    mock_category_objects.bulk_create.return_value = None

    # Form data with:
    # - CatA: same values → no update
    # - CatB: changed didSubjectAsk → update expected
    # - CatD: new category → create expected
    category_form_data = [
        {'categoryTitle': 'CatA', 'didSubjectAsk': True, 'categoryValue': 'ValA'},
        {'categoryTitle': 'CatB', 'didSubjectAsk': True, 'categoryValue': 'ValB'},  # changed didSubjectAsk
        {'categoryTitle': 'CatD', 'didSubjectAsk': False, 'categoryValue': 'ValD'},  # new category
    ]

    survey_id = 123

    # Call function under test
    survey.process_incategory_data(category_form_data, existing_categories, survey_id)

    # Assert bulk_create called once for the new category CatD
    created_arg = mock_category_objects.bulk_create.call_args[0][0]
    assert len(created_arg) == 1
    new_cat = created_arg[0]
    assert new_cat.categoryTitle == 'CatD'
    assert new_cat.categoryValue == 'ValD'
    assert new_cat.didSubjectAsk is False
    assert new_cat.survey_id == survey_id

    # Assert exclude called and .exists() on the same mock queryset
    existing_categories.exclude.assert_called_once()
    mock_exclude_qs.exists.assert_called_once()

    # Assert update called for CatB (changed)
    mock_category_objects.filter.assert_called()
    filter_mock.update.assert_called()


@pytest.mark.django_db
@patch('jdash.services.survey.transaction.atomic')
@patch('jdash.services.survey.Category.objects')
def test_process_incategory_data_no_changes(mock_category_objects, mock_atomic, category_instance_factory):
    # All categories in form data match existing → no create/update/delete

    existing_categories_dict = {
        'CatA': {'id': 1, 'value': 'ValA', 'didSubjectAsk': True},
    }

    existing_categories = MagicMock()
    existing_categories.exclude.return_value.exists.return_value = False  # no delete
    existing_categories.exclude.return_value.delete.return_value = None

    existing_categories.__contains__.side_effect = lambda x: x in existing_categories_dict
    existing_categories.__getitem__.side_effect = lambda k: existing_categories_dict[k]

    mock_category_objects.bulk_create.return_value = None
    filter_mock = MagicMock()
    mock_category_objects.filter.return_value = filter_mock
    filter_mock.update.return_value = None

    category_form_data = [
        {'categoryTitle': 'CatA', 'didSubjectAsk': True, 'categoryValue': 'ValA'},
    ]

    survey_id = 123
    survey.process_incategory_data(category_form_data, existing_categories, survey_id)

    # bulk_create, delete, update should not be called
    mock_category_objects.bulk_create.assert_not_called()
    existing_categories.exclude.return_value.delete.assert_not_called()
    mock_category_objects.filter.assert_not_called()
    mock_atomic.assert_called()


@pytest.mark.django_db
@patch('jdash.services.survey.transaction.atomic')
@patch('jdash.services.survey.Category.objects')
def test_process_incategory_data_empty_form_data(mock_category_objects, mock_atomic):
    # Test with empty form data deletes all existing categories

    existing_categories = MagicMock()
    existing_categories.exclude.return_value.exists.return_value = True
    existing_categories.exclude.return_value.delete.return_value = None

    survey_id = 123
    category_form_data = []

    survey.process_incategory_data(category_form_data, existing_categories, survey_id)

    # Should delete all categories (exclude called with empty list)
    existing_categories.exclude.assert_called_once_with(categoryTitle__in=set())
    existing_categories.exclude.return_value.delete.assert_called_once()
    mock_category_objects.bulk_create.assert_not_called()
    mock_category_objects.filter.assert_not_called()
    mock_atomic.assert_called()
