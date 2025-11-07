import logging , json
from jdash.apps import constants as constants
from jdash.textmessages import TextMessages as textmessages
logger = logging.getLogger("django")
def get_study_form_data(form,formset,request):
    form_data = {}

    form_data['name'] = form.cleaned_data.get('study_label')
    form_data['description'] = form.cleaned_data.get('study_description')
    form_data['duration'] = form.cleaned_data.get('study_duration')
    form_data['number-of-subjects'] = form.cleaned_data.get('number_of_subjects') #need to remove later after mobile changes
    form_data['number_of_subjects'] = form.cleaned_data.get('number_of_subjects')
    form_data['ema_checkbox'] = form.cleaned_data.get('ema_checkbox')
    if form.cleaned_data.get('ema_checkbox'):
        if form.cleaned_data.get('survey') != '':
            form_data['survey'] = int(form.cleaned_data.get('survey'))
        if "json_file" in request.FILES and request.FILES["json_file"] :
            ema_json_file = request.FILES["json_file"].read()
            form_data['survey'] = json.loads(ema_json_file)
        if "images_zip_file" in request.FILES and request.FILES["images_zip_file"] :
            #handle_uploaded_file(request.FILES["images_zip_file"],form_data['name'])
            form_data['images']= True
        else:
            form_data['images']= False
    else:
        form_data['images']= False
    form_data['is_test'] = form.cleaned_data.get('is_test')
    #form_data['passive_checkbox'] = form.cleaned_data.get('passive_checkbox')
    form_data['frequency'] = form.cleaned_data.get('recording_freq')
    form_data['sensor_list_limited'] = form.cleaned_data.get('sensor_list_limited')
    form_data['sensor-list'] = form.cleaned_data.get('sensor_list') #need to remove later after mobile changes
    form_data['sensor_list'] = form.cleaned_data.get('sensor_list') 
    if formset.is_valid():
        form_data['task_list'] = [] 
        for taskform in formset:
            task = {}
            if (validate_empty(taskform.cleaned_data.get('task_name') )):
                task['task_name'] = taskform.cleaned_data.get('task_name')
                task['task_preparation'] = taskform.cleaned_data.get('task_preparation') if taskform.cleaned_data.get('task_preparation') != None else 0
                task['task_duration'] = taskform.cleaned_data.get('task_duration')
                task['task_description'] = taskform.cleaned_data.get('task_description')
                form_data['task_list'].append(task)  
    else:
        form_data['task_list'] = [] 
    form_data[constants.field_name_labeling] = 0
    if len( form_data['task_list']) ==0 and len(form_data['sensor_list_limited'])  == 0: 
        form_data['active_labeling'] = 0
    
    if len( form_data['task_list']) > 0 and len(form_data['sensor_list_limited'])> 0 : 
        form_data['active_labeling'] = 1

    if len( form_data['sensor_list']) > 0 and len(form_data['task_list'])> 0 : 
        form_data['active_labeling'] = 2

    if len( form_data['sensor_list']) > 0 and len(form_data['sensor_list_limited'])> 0 : 
        form_data['active_labeling'] = 3


    form_data['enrolled_subjects'] = []        
    form_data['enrolled-subjects'] = [] #need to remove later after mobile changes
    logger.info("form_data %s",form_data)
    return form_data


def validate_empty(value):

    if (value != "" and value != None and value != "null"):
        return True
    return False

def get_survey_form_data(form):
    form_data = {}
    form_data["title"]= form.cleaned_data.get('title')
    form_data['description'] = form.cleaned_data.get('description')
    form_data['splitbyCategory'] = form.cleaned_data.get('splitbyCategory')
    form_data['scrolling'] = form.cleaned_data.get('scrolling')
    form_data["topN"]= -1

    logger.info("get_survey_form_data  cleaned date %s",form_data)
    return form_data


def get_question_form_data(form):
    form_data = {}
    form_data["title"]= form.cleaned_data.get('title')
    form_data["active"]= form.cleaned_data.get('active')
    form_data["sortId"]= form.cleaned_data.get('sortId')
    form_data['subText'] = form.cleaned_data.get('subText')
    form_data['frequency'] = form.cleaned_data.get('frequency')
    form_data['clockTime'] = form.cleaned_data.get('clockTime')
    form_data['clockTime_start'] = form.cleaned_data.get('clockTime_start')
    form_data['clockTime_end'] = form.cleaned_data.get('clockTime_end')
    form_data['activate_question'] = form.cleaned_data.get('activate_question')
    form_data['deactivate_question'] = form.cleaned_data.get('deactivate_question')
    form_data['activation_condition'] = form.cleaned_data.get('activation_condition') if form.cleaned_data.get('activation_condition') != None else ""
    form_data['deactivation_condition'] = form.cleaned_data.get('deactivation_condition') if form.cleaned_data.get('deactivation_condition') != None else ""
    form_data['nextDayToAnswer'] = form.cleaned_data.get('nextDayToAnswer')
    form_data['category'] = form.cleaned_data.get('category')
    form_data['imageURL'] = form.cleaned_data.get('imageURL')
    form_data['url'] = form.cleaned_data.get('url')
    form_data['questionType'] = form.cleaned_data.get('questionType')
    form_data['deactivateOnAnswer'] = form.cleaned_data.get('deactivateOnAnswer')
    form_data['deactivateOnDate'] = form.cleaned_data.get('deactivateOnDate') if form.cleaned_data.get('deactivateOnDate') != None else 0
    form_data['clockTime_timezone'] = form.cleaned_data.get('clockTime_timezone') if form.cleaned_data.get('clockTime_timezone') != None else "Europe/Berlin"
    logger.info("get_question_form_data  cleaned date %s",form_data)
    return form_data


def get_answer_form_data(formset):
    data = { 'answers': [] }
    for index,answer in enumerate(formset, start=1):
        form_data = {}
        logger.info("get_answer_form_data  cleaned date %s",answer.cleaned_data)
        form_data["answerSortId"] = index if answer.cleaned_data.get('answerSortId') is None \
                                                else answer.cleaned_data.get('answerSortId')
        form_data["text"]= answer.cleaned_data.get('text')
        form_data["answerSubText"]= answer.cleaned_data.get('answerSubText')
        form_data['value'] = answer.cleaned_data.get('value') if answer.cleaned_data.get('value') != None else 0.1
        form_data['defaultValue'] = answer.cleaned_data.get('defaultValue')  if answer.cleaned_data.get('defaultValue') != None else 0.1
        form_data['stepSize'] = answer.cleaned_data.get('stepSize')  if answer.cleaned_data.get('stepSize') != None else 0.1
        form_data['minValue'] = answer.cleaned_data.get('minValue')  if answer.cleaned_data.get('minValue') != None else 0.1
        form_data['maxValue'] = answer.cleaned_data.get('maxValue')  if answer.cleaned_data.get('maxValue') != None else 0.1
        form_data['minText'] = answer.cleaned_data.get('minText')  if answer.cleaned_data.get('minText') != None else ""
        form_data['maxText'] = answer.cleaned_data.get('maxText')  if answer.cleaned_data.get('maxText') != None else ""
        data['answers'].append(form_data)  
    return data

def get_blank_answer_object():
    answers = []
    answer = {}
    answer["answerSortId"] = 1
    answer["text"] = ""
    answer["answerSubText"] = "N"
    answer['value'] = 0.1
    answer['defaultValue'] = 0.1
    answer['stepSize'] = 0.1
    answer['minValue'] = 0.1
    answer['maxValue'] = 0.1
    answer['minText'] = ""
    answer['maxText'] = "" 
    answers.append(answer)
    return answers


def get_category_form_data(formset):
    form_data = {} 
    form_data['category_list'] = []
    for index, category_form in enumerate(formset, start=1):
        category = {}
        if (validate_empty(category_form.cleaned_data.get('categoryTitle') )):
            category['categoryTitle'] = category_form.cleaned_data.get('categoryTitle')
            category['categoryValue'] = index if category_form.cleaned_data.get('categoryValue') is None \
                                                else category_form.cleaned_data.get('categoryValue')
            #category['didSubjectAsk'] = category_form.cleaned_data.get('didSubjectAsk') 
            form_data['category_list'].append(category)  
    return form_data

def get_contactus_form_data(form):
    full_name = form.cleaned_data.get('fullname')
    email = form.cleaned_data.get('email')
    message = form.cleaned_data.get('message')

    return full_name,email,message

def get_notification_form_data(form):
    message_title = form.cleaned_data.get('message_title')
    message_text = form.cleaned_data.get('message_text')
    receivers = form.cleaned_data.get('receivers')

    return message_title,message_text,receivers


def get_info_texts():
    info_texts = {
        "ema": textmessages.info_text_ema,
        "passive_monitoring": textmessages.info_text_passive_monitoring,
        "no_labelling": textmessages.info_text_no_labelling,
        "active_labelling": textmessages.info_text_active_labelling,
        "manual_active_labelling": textmessages.info_text_manual_active_labelling,
        "partial_active_labelling": textmessages.info_text_partial_active_labelling
    }

    return info_texts

def get_help_texts_for_study_form():
    help_texts = {
        "title": textmessages.help_text_survey_title,
        "description": textmessages.help_text_survey_description,
        "splitbyCategory": textmessages.help_text_survey_splitByCategory,
        "topN": textmessages.help_text_survey_topN,
    }

    return help_texts
 
def get_help_texts_for_survey_form():
    help_texts = {
        "title": textmessages.help_text_survey_title,
        "description": textmessages.help_text_survey_description,
        "splitbyCategory": textmessages.help_text_survey_splitByCategory,
        "scrolling": textmessages.help_text_survey_scrolling,
        "topN": textmessages.help_text_survey_topN,
    }

    return help_texts

def get_help_texts_for_question_form():
    help_texts = {
        "sortId": textmessages.help_text_survey_question_sortId,
        "title": textmessages.help_text_survey_question_title,
        "description": textmessages.help_text_survey_question_description,
        "category": textmessages.help_text_survey_question_category,
        "type": textmessages.help_text_survey_question_type,
        "firstDayToAnswer": textmessages.help_text_survey_question_firstDayToAnswer,
        "imageURL": textmessages.help_text_survey_question_imageURL,
        "url": textmessages.help_text_survey_question_url,
        "frequency": textmessages.help_text_survey_question_frequency,
        "clockTime": textmessages.help_text_survey_question_clockTime,
        "clockTime_start": textmessages.help_text_survey_question_clockTime_start,
        "clockTime_end": textmessages.help_text_survey_question_clockTime_end,
        "activate_question": textmessages.help_text_survey_category_activate_question,
        "deactivate_question": textmessages.help_text_survey_category_deactivate_question,
        "activation_condition": textmessages.help_text_survey_category_activation_condition,
        "deactivation_condition": textmessages.help_text_survey_category_deactivation_condition,
        "deactivateOnAnswer": textmessages.help_text_survey_question_deactivateOnAnswer,
        "deactivateOnDate": textmessages.help_text_survey_question_deactivateOnDate,
        "answerForm": textmessages.help_text_survey_question_answerForm,
    }

    return help_texts

def get_help_texts_for_category_form():
    help_texts = {
        "title": textmessages.help_text_survey_title,
        "value": textmessages.help_text_survey_description,
        "didSubjectAsk": textmessages.help_text_survey_splitByCategory
    }

    return help_texts

def get_help_texts_for_study_form():
    help_texts = {
        "title": textmessages.help_text_survey_title,
        "description": textmessages.help_text_survey_description,
        "splitbyCategory": textmessages.help_text_survey_splitByCategory,
        "topN": textmessages.help_text_survey_topN,
    }

    return help_texts
