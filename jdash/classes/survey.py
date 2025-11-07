###########################################################################
####           survey.py
####           this file contains all the service methods related to studies
####           initial version written by mnarava
####
####
###########################################################################
import logging
from django.db import transaction
from jdash.apps import constants as constants
from jdash.classes.dbutils import retrieve_download_questions_for_survey, retrieve_survey_details
from jdash.classes.dbutils import delete_answer_in_db,update_answer_in_db,create_answer_in_db
from jdash.classes.dbutils import retrieve_all_categories_for_survey,retrieve_all_answers_for_questions
from jdash.models import Question
from jdash.models import Category
from jdash.classes.datahelper import get_blank_answer_object
logger = logging.getLogger("django")

class Survey:
    """Class representing a Survey"""
    def __init__(self, id, title, description,splitbyCategory,scrolling,topN):
        self.id = id
        self.title = title
        self.description = description
        self.splitbyCategory = splitbyCategory
        self.scrolling = scrolling
        self.topN = topN
        self.questions = []

    def add_question(self, question_dict):
        question_id = question_dict['id']
        self.questions[question_id] = { 
            'id': question_id,
            'title': question_dict.get('title', question_dict['text']),
            'questionType': question_dict.get('questionType', question_dict['type']),
            'subText': question_dict.get('subText', question_dict['subText']),
            'category': question_dict.get('category', question_dict['category']),
            'frequency': question_dict.get('frequency', question_dict['frequency']),
            'clockTime': question_dict.get('clockTime', question_dict['clockTime']),
            'nextDayToAnswer': question_dict.get('nextDayToAnswer', question_dict['nextDayToAnswer']),
            'imageURL': question_dict.get('imageURL', question_dict['imageURL']),
            'url': question_dict.get('url', question_dict['url']),
            'deactivateOnAnswer': question_dict.get('deactivateOnAnswer', question_dict['deactivateOnAnswer']),
            'deactivateOnDate': question_dict.get('deactivateOnDate', question_dict['deactivateOnDate']),
            'answers': []
        }

    def add_answer_to_question(self, question_id, answer_dict):
        if question_id in self.questions:
            question = self.questions[question_id]
            answer_id = answer_dict['id']
            question['answers'][answer_id] = {
                'id': answer_id,
                'answerText': answer_dict.get('answerText', answer_dict['text']),
                'answerValue': answer_dict.get('answerValue', answer_dict['value']),
                'defaultValue': answer_dict.get('defaultValue', answer_dict['defaultValue']),
                'stepSize': answer_dict.get('stepSize', answer_dict['stepSize']),
                'minValue': answer_dict.get('minValue', answer_dict['minValue']),
                'maxValue': answer_dict.get('maxValue', answer_dict['maxValue']),
                'minText': answer_dict.get('minText', answer_dict['minText']),
                'maxText': answer_dict.get('maxText', answer_dict['maxText'])
            }
        else:
            logger.info(f"Question ID {question_id} not found.")

    def update_question(self, question_id, question_dict):
        if question_id in self.questions:
            question = self.questions[question_id]
            question['title'] = question_dict.get('title', question['title'])
            question['questionType'] = question_dict.get('questionType', question['questionType'])
            question['subText'] = question_dict.get('subText', question['subText'])
            question['category'] = question_dict.get('category', question['category'])
            question['frequency'] = question_dict.get('frequency', question['frequency'])
            question['clockTime'] = question_dict.get('clockTime', question['clockTime'])
            question['nextDayToAnswer'] = question_dict.get('nextDayToAnswer', question['nextDayToAnswer'])
            question['imageURL'] = question_dict.get('imageURL', question['imageURL'])
            question['url'] = question_dict.get('url', question['url'])
            question['deactivateOnAnswer'] = question_dict.get('deactivateOnAnswer', question['deactivateOnAnswer'])
            question['deactivateOnDate'] = question_dict.get('deactivateOnDate', question['deactivateOnDate'])
            question['answers'] = question_dict.get('answers', question['answers'])

        else:
            logger.info(f"Question ID {question_id} not found.")

    def update_answer(self, question_id, answer_id,answer_dict):
        if question_id in self.questions and answer_id in self.questions[question_id]['answers']:
            answer = self.questions[question_id]['answers'][answer_id]
            answer['answerText'] = answer_dict.get('text', answer['text'])
            answer['answerValue'] = answer_dict.get('value', answer['value'])
            answer['defaultValue'] = answer_dict.get('defaultValue', answer['defaultValue'])
            answer['stepSize'] = answer_dict.get('stepSize', answer['stepSize'])
            answer['minValue'] = answer_dict.get('minValue', answer['minValue'])
            answer['maxValue'] = answer_dict.get('maxValue', answer['maxValue'])
            answer['minText'] = answer_dict.get('minText', answer['minText'])
            answer['maxText'] = answer_dict.get('maxText', answer['maxText'])
        else:
            logger.info(f"Question ID {question_id} or Answer ID {answer_id} not found.")

    def to_json(self):
        # Convert questions and answers to lists for JSON serialization
        survey_data = {
            'title': self.title,
            'description': self.description,
            'questions': [{**q, 'answers': list(q['answers'].values())} for q in self.questions.values()]
        }
        return survey_data

    @staticmethod
    def from_json(data):
        survey = Survey(data['title'], data['description'])
        for question in data['questions']:
            survey.add_question(question)
            for answer in question['answers']:
                survey.add_answer_to_question(question['id'], answer['id'], **answer)
        return survey

    
def generate_survey_json_for_download(survey_id):
    """Method  to generate json file for the survey"""
    survey_json = {} 
    question_data = retrieve_download_questions_for_survey(survey_id) 
    category_data = retrieve_all_categories_for_survey(survey_id)
    survey_json[constants.key_name_questions] = question_data
    survey_json[constants.key_name_categories] = category_data
    survey_details = retrieve_survey_details(survey_id)
    survey_json['id'] = survey_details['id']
    survey_json['title'] = survey_details['title']
    survey_json['description'] = survey_details['description']
    survey_json['topN'] = survey_details['topN']
    #logger.info(survey_json)
    return survey_json

def check_and_enter_answer_in_db(question_id,form_data):
    """Method  representing a Survey"""
    for index,answer in enumerate(form_data):        
        logger.info("storing other answer data %s",answer)
        #answer['answerSortId'] = answer["id"]
        create_answer_in_db(question_id,answer)

def update_answer_choice_text_details(question_id,form_data,answer_id_list):
    """Method  representing a Survey"""
    logger.info('update_answer_choice_text_details %s ::%s',form_data,answer_id_list)
    if len(form_data) == len(answer_id_list):
        logger.info("updating choices")
        current_answer_map = list(zip(answer_id_list,form_data))
        for answer_id,answer in current_answer_map:
            logger.info("updating exisiting choices %s",answer_id)
            #answer['answerSortId'] = answer["id"]
            update_answer_in_db( answer, answer_id)
    elif len(answer_id_list) > len(form_data):
        logger.info("deleting choices")
        # deletion if text has removed
        remaining_ids = answer_id_list[len(form_data):]
        for answer_id in remaining_ids:
            logger.info("deleting answer with id %s",answer_id)
            delete_answer_in_db(answer_id)
    else:
        logger.info("adding new choices")
        remaining_answers = form_data[len(answer_id_list):]
        for answer_data in remaining_answers:           
                logger.info("creating new choices %s",answer_data)
                #answer_data['answerSortId'] = answer_data["id"]
                create_answer_in_db(question_id,answer_data)

    return True

def update_other_answer_details(question_id,form_data,answer_id_list):
    """Method  representing a Survey"""
    logger.debug('update_other_answer_detials ')
    current_answer_map = list(zip(answer_id_list,form_data))
    for answer_id,answer in current_answer_map:
        logger.info("updating: answer with: %s :for question: %s",answer,question_id)
        #answer['answerSortId'] = answer["id"]
        answer['id'] = answer_id
        logger.info("updating answer %s",answer)
        update_answer_in_db(answer,answer_id)


def _direction_flag(old_type: int, new_type: int) -> int:
    """
    Direction flag for group change, with 0 included in the 'other (>=3)' group.
    Returns:
        +1 : choice (1/2) -> other (0 or >=3)
        -1 : other (0 or >=3) -> choice (1/2)
         0 : same group (no crossing)
    """
    old_is_choice = old_type in (1, 2)
    new_is_choice = new_type in (1, 2)

    if old_is_choice and not new_is_choice:
        return +1
    if not old_is_choice and new_is_choice:
        return -1
    return 0


def check_question_type_change(question_id, question_obj):
    """
    Returns (crossed_groups: bool, direction_flag: int)
    direction_flag in {+1, -1, 0} as defined above.
    """
    persist_question = Question.objects.only("id", "questionType").get(id=question_id)
    try:
        old_type = int(persist_question.questionType)
        new_type = int(question_obj["questionType"])
    except (KeyError, TypeError, ValueError):
        logger.warning("Invalid or missing questionType in payload/state")
        return  0

    flag = _direction_flag(old_type, new_type)

    if flag == 0:
        grp = "CHOICE" if old_type in (1, 2) else "OTHER(0 or ≥3)"
        logger.info("Question type stayed within %s group: %s → %s", grp, old_type, new_type)
        return  0

    direction = "choice_to_other" if flag == +1 else "other_to_choice"
    logger.info("Question type crossed groups (%s): %s → %s", direction, old_type, new_type)
    return flag


def update_sortid_of_questions(question_id,new_sequence_id):
    """Method  to reoder the sortid"""
    # updating the sequence id of the question of there is change
    question  = Question.objects.get(id = question_id)
    logger.info("update_sortid_of_questions %s :: %s",question, new_sequence_id)
    old_sequence_id = question.sortId
    question_id = question.id

    if new_sequence_id > old_sequence_id: 
        logger.info("greater than")
        questions_to_update = Question.objects.filter(
            survey=question.survey,
            sortId__gt=old_sequence_id,
            sortId__lte=new_sequence_id
        ).exclude(id=question_id).order_by('sortId')

        for q in questions_to_update:
            old_sort_id = q.sortId
            q.sortId -= 1
            logger.info("Shifted down: %s from %d to %d", q, old_sort_id, q.sortId)
            q.save()

    elif new_sequence_id < old_sequence_id:
        logger.info("less than")
        questions_to_update = Question.objects.filter(
            survey=question.survey,
            sortId__gte=new_sequence_id,
            sortId__lt=old_sequence_id
        ).exclude(id=question_id).order_by('-sortId')

        for q in questions_to_update:
            old_sort_id = q.sortId
            q.sortId += 1
            logger.info("Shifted up: %s from %d to %d", q, old_sort_id, q.sortId)
            q.save()

    # Finally, assign the updated sortId to the moved question
    question.sortId = new_sequence_id
    question.save()
    logger.info("Set moved question %s to new sortId: %d", question, new_sequence_id)
    logger.info("update_sortid_of_questions %s",new_sequence_id)
    return True

# Function to process category data
def process_incategory_data(category_form_data, existing_categories, survey_id):
    """
    Compare category form data with the existing database data.
    Create new entries for missing categories and update existing ones if needed.

    Args:
        category_data (list): New category data from the form.
        existing_categories (QuerySet): Existing categories in the database.
        survey_id (int): Survey ID to associate with categories.
    """
    new_categories = []
    updated_categories = []
    # Extract category names from form data
    category_names_in_form = {cat['categoryTitle'] for cat in category_form_data}

    # Identify categories to delete (those in the database but not in the form data)
    categories_to_delete = existing_categories.exclude(categoryTitle__in=category_names_in_form)

    # Iterate through the form data
    for form_category in category_form_data:
        category_name = form_category['categoryTitle']
        category_didsubject_ask = form_category['didSubjectAsk']
        category_value = form_category['categoryValue']

        if category_name in existing_categories:
            # Check if the value has changed
            existing_category = existing_categories[category_name]
            # Check if the value or 'didSubjectAsk' field has changed
            value_changed = existing_category['value'] != category_value
            didsubjectask_changed = existing_category['didSubjectAsk'] != category_didsubject_ask

            if value_changed or didsubjectask_changed:
                # Add to the update list
                updated_categories.append({
                    'id': existing_category['id'],
                    'categoryTitle': category_name,
                    'didSubjectAsk': category_didsubject_ask,
                    'categoryValue': category_value,
                })
        else:
            # Add to the create list if it's a new category
            new_categories.append(
                Category(categoryTitle=category_name, categoryValue=category_value,
                         didSubjectAsk=category_didsubject_ask, survey_id=survey_id)
            )
    
    # Bulk create and update
    with transaction.atomic():
        if new_categories:
            Category.objects.bulk_create(new_categories)
        if categories_to_delete.exists():
            categories_to_delete.delete()
        for updated in updated_categories:
            Category.objects.filter(id=updated['id']).update(
                categoryTitle=updated['categoryTitle'],
                categoryValue=updated['categoryValue'],
                didSubjectAsk=updated['didSubjectAsk'])

# Function to process category data
def process_category_data(category_form_data, existing_categories, survey_id):
    """
    Compare category form data with the existing database data.
    Create new entries for missing categories and update existing ones if needed.
    
    Args:
        category_data (list): New category data from the form.
        existing_categories (QuerySet): Existing categories in the database.
        survey_id (int): Survey ID to associate with categories.
    """
    # Extract category details from form data
    category_data_dict = {
        data['categoryTitle']: {
            'categoryValue': data['categoryValue'],
            'didSubjectAsk': data['didSubjectAsk'],
        } 
        for data in category_form_data
    }
                                                                               
    # Identify categories to create, update, or delete
    existing_category_names = set(existing_categories.values_list('categoryTitle', flat=True))
    form_category_names = set(category_data_dict.keys())

    categories_to_create = form_category_names - existing_category_names
    categories_to_update = form_category_names & existing_category_names
    categories_to_delete = existing_category_names - form_category_names
    # Prepare lists for bulk operations
    new_categories = [
        Category(
            categoryTitle=name, 
            categoryValue=category_data_dict[name]['categoryValue'], 
            didSubjectAsk=category_data_dict[name]['didSubjectAsk'], 
            survey_id=survey_id
        )
        for name in categories_to_create
    ]

    # Bulk create, update, and delete
    with transaction.atomic():
        # Create new categories
        if new_categories:
            Category.objects.bulk_create(new_categories)

        # Update existing categories
        for name in categories_to_update:
            category = existing_categories.get(categoryTitle=name)
            form_data = category_data_dict[name]
            if category.categoryValue != form_data['categoryValue'] or category.didSubjectAsk != form_data['didSubjectAsk']:
                category.categoryValue = form_data['categoryValue']
                category.didSubjectAsk = form_data['didSubjectAsk']
                category.save()

        # Delete categories not in the form data
        if categories_to_delete:
            existing_categories.filter(categoryTitle__in=categories_to_delete).delete()

