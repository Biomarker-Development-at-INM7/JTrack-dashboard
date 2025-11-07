import json, logging
from django.db.models import Q
from datetime import date
from operator import itemgetter
from jdash.apps import constants as constants
from django.contrib.auth.models import User, Group
from django.contrib.auth.models import Permission
from jdash.models import Study as studymodel
from jdash.models import Question as questionModel
from jdash.models import Answer as answerModel
from jdash.models import Survey as surveyModel
from jdash.models import Category as categoryModel
from jdash.models import FileDownloadToken as downloadFile
from jdash.models import QualityControlTests as qctestsModel
from jdash.interface.session_manager import SessionManager

logger = logging.getLogger("django")




def custom_serializer(queryset):
    '''
    Serializer for the study object
    '''
    result = []
    for obj in queryset:
        item = {

            "id": obj['id'],
            "title": obj['title'],
            "is_test": obj['is_test'],
            "duration": obj['duration'],
            "numberOfSubjects": obj['numberOfSubjects'],
            "description": obj['description'],
            "enrolled_subjects": obj['enrolled_subjects'],
            "owner_id": obj['owner_id'],
            "passive_monitoring": obj['passive_monitoring'],
            "frequency": obj['frequency'],
            "sensor_list": obj['sensor_list'],
            "labeling": obj['labeling'],
            "survey": obj['survey_id'],
            # Handle datetime or other complex types explicitly
            "createdDate": obj['createdDate'].strftime('%Y-%m-%d') if isinstance(obj['createdDate'], date) else None,
        }
        result.append(item)
    return json.dumps(result)


def answer_download_serializer(queryset):
    '''
    update_question_in_db
    '''
    result = []
    for obj in queryset:
        item = {
            "db_id": obj['id'],
            "id": obj['answerSortId'],
            "text": obj['text'],
            "subText" : obj['answerSubText'],
            "value": obj['value'],
            "defaultValue": obj['defaultValue'],
            "stepSize": obj['stepSize'],
            "minVal": obj['minValue'],
            "maxVal": obj['maxValue'],
            "minText": obj['minText'],
            "maxText": obj['maxText'],

        }
        result.append(item)
    return json.dumps(result)


def answer_serializer(queryset):
    '''
    update_question_in_db
    '''
    result = []
    for obj in queryset:
        text_value = obj.get('text')
        if text_value is None:
            # decide what to do when there's no text—e.g. skip, set to empty string, etc.
            text_value = ""
        item = {
            "db_id": obj['id'],
            "id": obj['answerSortId'],
            "text": text_value,
            "subText" : obj['answerSubText'],
            "value": obj['value'],
            "defaultValue": obj['defaultValue'],
            "stepSize": obj['stepSize'],
            "minValue": obj['minValue'],
            "maxValue": obj['maxValue'],
            "minText": obj['minText'],
            "maxText": obj['maxText'],

        }
        result.append(item)
    return json.dumps(result)

def survey_serializer(queryset):
    '''
    update_question_in_db
    '''
    result = []
    for obj in queryset:
        item = {

            "id": obj['id'],
            "title": obj['title'].encode('utf-8').decode('utf-8'),
            "description": obj['description'].encode('utf-8').decode('utf-8'),
            "topN": obj['topN'],
            "splitbyCategory" : obj['splitbyCategory'],
            "scrolling" : obj['scrolling'],
            # Handle datetime or other complex types explicitly
            "createdDate": obj['createdDate'].strftime('%Y-%m-%d') if isinstance(obj['createdDate'], date) else None,
        }
        result.append(item)
    return json.dumps(result)

def category_serializer(queryset):
    result = []
    for category_data in queryset:
        item = {
            "id": category_data['id'],
            "categoryTitle": category_data['categoryTitle'],
            "categoryValue" : category_data['categoryValue'],
            "didSubjectAsk" : category_data['didSubjectAsk']
        }
        result.append(item)
    return json.dumps(result)

def question_db_serializer(queryset):
    result = []
    for question_data in queryset:
        item = {
            "db_id": question_data['id'],
            "id": question_data['sortId'],
            "sortId": question_data['sortId'],
            "title": question_data['title'],
            "active": 1 if question_data['active'] else 0,
            "subText" : question_data['subText'],
            "frequency" : question_data['frequency'],
            "clockTime" : question_data['clockTime'],
            "clockTime_start" : question_data['clockTime_start'],
            "clockTime_end" : question_data['clockTime_end'],
            "nextDayToAnswer" :question_data['nextDayToAnswer'],
            "category" : question_data['category'],
            "imageURL" : question_data['imageURL'],
            "url" : question_data['url'],
            "questionType" : question_data['questionType'],
            "questionType" : question_data['questionType'],
            "deactivateOnAnswer" : question_data['deactivateOnAnswer'],
            "deactivateOnDate" : question_data['deactivateOnDate'],
            "activate_question" : question_data['activate_question'], 
            "deactivate_question" : question_data['deactivate_question'],
            "activation_condition" : question_data['activation_condition'],
            "deactivation_condition" : question_data['deactivation_condition'],
            "clockTime_timezone" : question_data['clockTime_timezone'] 
        }
        result.append(item)
    return json.dumps(result)

def category_serializer(queryset):
    result = []
    for category_data in queryset:
        item = {
            "id": category_data['id'],
            "categoryTitle": category_data['categoryTitle'].encode('utf-8').decode('utf-8'),
            "categoryValue" : category_data['categoryValue'],
            "didSubjectAsk" : category_data['didSubjectAsk']
        }
        result.append(item)
    return json.dumps(result)




def question_db_list_serializer(value):
    '''
    Serializer for the question list
    '''
    if value is "":
        return []
    if isinstance(value, str):
        return [int(value)]
    else:
        return [int(x) for x in value.split(',')]

def question_string_serializer(value):
    '''
    Serializer for the question list
    '''
    if len(value) == 0:
        return ""
    elif len(value) == 1:
        return value[0]
    else:
        return ",".join(str(x) for x in value)

def modify_questions_list_to_string(question):
    if isinstance(question['activate_question'], list):
        question['activate_question'] =question_string_serializer(question['activate_question'])
    if isinstance(question['deactivate_question'], list):
        question['deactivate_question'] = question_string_serializer(question['deactivate_question'])
    if isinstance(question['clockTime_start'], list):
        question['clockTime_start'] = question_string_serializer(question['clockTime_start'])
    if isinstance(question['clockTime_end'], list):
        question['clockTime_end'] = question_string_serializer(question['clockTime_end'])

    return question

def question_serializer(queryset):
    '''
    question_serializer
    '''
    result = []
    for question_data in queryset:
        clocktime_str = question_data['clockTime']        
        clocktime_start_str = ""
        clocktime_end_str = ""
        activate_question_value = question_data['activate_question']
        deactivate_question_value = question_data['deactivate_question']
        activate_question_str = ""
        deactivate_question_str = ""
        
        if question_data['clockTime_start'] not in (None, ""," ", []):
            clock_start_raw = question_data['clockTime_start']
            # If it's a list (expected case), join it
            if isinstance(clock_start_raw, list):
                if len(clock_start_raw) > 1:
                    clocktime_start_str = ";".join(map(str, clock_start_raw))
                    clocktime_str = 0
                    clocktime_end_str = ";".join(map(str, question_data['clockTime_end']))
            # logic to handle the migration of Clocktime to clockTime_start not to effect the study.json
                else:
                    if len(question_data['clockTime_end']) == 0:
                        clocktime_start_str = str(clock_start_raw[0])
                        clocktime_str = int(clocktime_start_str)
                        clocktime_start_str = ""
                    else:
                        clocktime_start_str = str(clock_start_raw[0])
                        clocktime_str = 0
                        clocktime_end_str = ";".join(map(str, question_data['clockTime_end']))
        else:
            clocktime_str = 1

        if activate_question_value not in (None, "", []):
            if isinstance(activate_question_value, list):
                if len(activate_question_value) > 1:
                    activate_question_str = ";".join(map(str,activate_question_value))
                else:
                    activate_question_str = str(activate_question_value[0])
            else:
                activate_question_str = str(activate_question_value).replace(",", ";")
            
            
        if deactivate_question_value not in (None, "", []):
            if isinstance(deactivate_question_value, list):
                if len(deactivate_question_value) > 1:
                    deactivate_question_str = ";".join(map(str,deactivate_question_value))
                else:
                    deactivate_question_str = str(deactivate_question_value[0])
            else:
                deactivate_question_str = str(deactivate_question_value).replace(",", ";")

        if question_data['activation_condition'] == "None" or question_data['activation_condition'] is None:
            question_data['activation_condition'] = ""
        if question_data['deactivation_condition'] == "None" or question_data['deactivation_condition'] is None:
            question_data['deactivation_condition'] = ""
        item = {
            "db_id": question_data['id'],
            "id": question_data['sortId'],
            "title": question_data['title'],
            "active": 1 if question_data['active'] else 0,
            "subText" : question_data['subText'],
            "frequency" : question_data['frequency'],
            "clockTime" : clocktime_str,
            "clockTime_start" : clocktime_start_str,
            "clockTime_end" : clocktime_end_str,
            "nextDayToAnswer" :question_data['nextDayToAnswer'],
            "category" : question_data['category'],
            "imageURL" : question_data['imageURL'],
            "url" : question_data['url'],
            "questionType" : question_data['questionType'],
            "deactivateOnAnswer" : question_data['deactivateOnAnswer'],
            "deactivateOnDate" : question_data['deactivateOnDate'],
            "activate_question" : activate_question_str ,
            "deActivate_question" : deactivate_question_str,
            "activation_condition" : question_data['activation_condition'],
            "deActivation_condition" : question_data['deactivation_condition'],
            "clockTime_timezone" : question_data['clockTime_timezone'] 
        }
        result.append(item)
    return json.dumps(result)



def normalize_question_data_defaults(question_data):
    """
    Normalizes the default values in the given question data dictionary.
    This function ensures that specific fields in the `question_data` dictionary
    have appropriate default values if they are `None` or empty. It also applies
    additional logic to set the `clockTime` field based on the values of
    `clockTime_start` and `clockTime_end`.
    Args:
        question_data (dict): A dictionary containing question data fields.
    Returns:
        dict: The updated `question_data` dictionary with normalized default values.
    """

    if question_data[constants.field_name_activate_question] is None \
            or question_data[constants.field_name_activate_question] == "":
        question_data[constants.field_name_activate_question] = []

    if question_data[constants.field_name_deactivate_question] is None \
            or question_data[constants.field_name_deactivate_question] == "":
        question_data[constants.field_name_deactivate_question] = []

    if question_data[constants.field_name_clockTime_start] is None \
            or question_data[constants.field_name_clockTime_start] == "":
        question_data[constants.field_name_clockTime_start] = []

    if question_data[constants.field_name_clockTime_end] is None \
            or question_data[constants.field_name_clockTime_end] == "":
        question_data[constants.field_name_clockTime_end] = []

    if question_data[constants.field_name_clockTime] is None \
            or question_data[constants.field_name_clockTime] == "":
                question_data[constants.field_name_clockTime] = 0

    if int(question_data[constants.field_name_clockTime]) > 0  and (question_data[constants.field_name_clockTime_start] == "" \
        and question_data[constants.field_name_clockTime_end] == ""):
        question_data[constants.field_name_clockTime_start] = question_data[constants.field_name_clockTime]

    if int(question_data[constants.field_name_clockTime]) == 0 and (len(question_data[constants.field_name_clockTime_start]) == 0 \
        and len(question_data[constants.field_name_clockTime_end]) == 0):
        question_data[constants.field_name_clockTime] = 1

    if question_data[constants.field_name_activation_condition] is None:
        question_data[constants.field_name_activation_condition] = ""

    if question_data[constants.field_name_deactivation_condition] is None:
        question_data[constants.field_name_deactivation_condition] = ""

    # if clockTime_start has one value and clockTime_end is empty, add clockTime_start value to clockTime
    if len(question_data[constants.field_name_clockTime_start]) == 1 \
        and len(question_data[constants.field_name_clockTime_end]) == 0:
        question_data[constants.field_name_clockTime] = question_data[constants.field_name_clockTime_start][0]

    if len(question_data[constants.field_name_clockTime_start]) > 1 :
        question_data[constants.field_name_clockTime] = 0
    

    return question_data
