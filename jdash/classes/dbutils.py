import json, logging
from django.db.models import Q
from django.db import transaction
from django.db.models import F
from datetime import date
from operator import itemgetter
from django.contrib.auth.models import User, Group
from django.contrib.auth.models import Permission
from jdash.apps import constants as constants
from jdash.models import Study as studymodel
from jdash.models import Question as questionModel
from jdash.models import Answer as answerModel
from jdash.models import Survey as surveyModel
from jdash.models import Category as categoryModel
from jdash.models import FileDownloadToken as downloadFile
from jdash.models import QualityControlTests as qctestsModel
from jdash.interface.session_manager import SessionManager
from .utils import custom_serializer, question_db_serializer, survey_serializer
from .utils import question_serializer, answer_serializer, category_serializer
from .utils import answer_download_serializer
logger = logging.getLogger("django")

def set_email_for_user(username,email):
    ''' Set the email of user'''
    # Retrieve the user
    user = User.objects.get(username=username)
    user.email = email
    # Save the user
    user.save()

def retireve_all_studies_for_user(user):
    '''
    update_question_in_db
    '''
    queryset = studymodel.objects.none()
    groupNames = []
    for gp in user.groups.all():
        groupNames.append(gp.name)
    if "administrator" in groupNames:
        queryset = studymodel.objects.filter(closed=False).values()
    else:
        combined_query = Q()
        for gname in groupNames:
            searchString = gname.split("_group")[0]
            # Combine queries using OR (|)
            combined_query |= Q(title__startswith=searchString, closed=False)
        # Apply the combined query to get the final queryset
        queryset = studymodel.objects.filter(combined_query)

    # Optional: use .values() if you need a QuerySet of dictionaries
    queryset_values = queryset.values()

    # Assuming you're iterating over a queryset
    data = custom_serializer(queryset_values)
  
    return data

def get_group_name_for_user(user):
    '''
    update_question_in_db
    '''
    group = constants.default_group
    groupNames = [gp.name for gp in user.groups.all()]

    for group_name in groupNames:
        if group_name in constants.group_mapping:
            group = constants.group_mapping[group_name]
            break
    return group

def create_new_study_in_db(user, form_data,survey,images_url):
    '''
    update_question_in_db
    '''
    logger.info("create_new_study_in_db %s",form_data)

    frequency = form_data[constants.field_name_frequency]
    labeling = form_data[constants.field_name_labeling]
    sensor_list = form_data[constants.field_name_sensor_list]

    # if ema study add survey id to survey column
    # Check for task list - how formset can be in db
    studymodel.objects.create(title=form_data['name'], 
                            description=form_data['description'],
                            numberOfSubjects=form_data['number-of-subjects'], 
                            enrolled_subjects="000",
                            duration=form_data['duration'], 
                            is_test=form_data['is_test'], 
                            owner=user,
                            passive_monitoring = True if len(sensor_list) >0 else False,
                            frequency = frequency,
                            labeling = labeling,
                            sensor_list = sensor_list,
                            ecological_momentary_assessment = True if survey is not None else False,
                            survey = survey ,
                            images = images_url)
    
    create_new_study_group(user, form_data)

def create_new_study_group(user, form_data):
    '''
    update_question_in_db
    '''
    study_group, created = Group.objects.get_or_create(name=form_data['name'] + '_group')
    assign_all_group_permissions(user.username, study_group.name)

def create_new_survey_in_db(form,user):
    ''' Create new survey in the database'''
    owner = User.objects.get(username=user.username)
    logger.info("create_new_survey_in_db %s",owner.id)
    survey = surveyModel.objects.create(title=form["title"],
                                        description=form["description"],
                                        topN=form["topN"],
										splitbyCategory = form['splitbyCategory'] if 'splitbyCategory' in form else 0,
                                        scrolling = form['scrolling'] if 'scrolling' in form else 'H',
                                        owner_id=owner.id)
    return survey

def update_survey_info_in_db(form,survey_id):
    ''' Update survey information in the database'''
    survey = surveyModel.objects.get(id=survey_id)

    survey.title = form["title"]
    survey.description = form["description"]
    survey.topN = form["topN"]
    survey.splitbyCategory = form['splitbyCategory'] if 'splitbyCategory' in form else 0
    survey.scrolling = form['scrolling'] if 'scrolling' in form else 'H'

    survey.save()
    
    return survey

def create_survey_in_db( study_name,survey_dict,user):
    '''
    update_question_in_db
    '''
    # Create survey
    survey = surveyModel.objects.create(title=study_name,
                                        description="",
                                        topN=survey_dict[constants.key_name_topN],
                                        splitbyCategory = survey_dict['splitbyCategory'] if 'splitbyCategory' in survey_dict else 0,
                                        scrolling = survey_dict['scrolling'] if 'scrolling' in survey_dict else 'H',
                                        owner=user)
    logger.info("create_survey_in_db::start::%s",survey)
    if "categories" in survey_dict:
        create_categories_in_db_from_data(survey.id,survey_dict['categories'])
    # Create questions
    for question_data in survey_dict['questions']:
        if question_data['clockTime_start'].strip():
            question_data['clockTime_start'] = [int(x) for x in question_data['clockTime_start'].split(';')]
        if question_data['clockTime_end'].strip():
            question_data['clockTime_end'] = [int(x) for x in question_data['clockTime_end'].split(';')]
        if question_data['activate_question'].strip():
            if question_data['activate_question'] != "" and ';' in question_data['activate_question']:
                question_data['activate_question'] = [int(x) for x in question_data['activate_question'].split(';')]
        if question_data['deActivate_question'].strip():
            if question_data['deActivate_question'] != "" and ';' in question_data['deActivate_question']:
                question_data['deActivate_question'] = [int(x) for x in question_data['deActivate_question'].split(';')]

        if question_data[constants.field_name_clockTime] > 0 and (question_data[constants.field_name_clockTime_start] == "" \
            and question_data[constants.field_name_clockTime_end]== "" ):
            question_data[constants.field_name_clockTime_start] = [int(question_data[constants.field_name_clockTime])]

        question = questionModel.objects.create(
            survey=survey,
            title= question_data['title'],
            active= 1,
            sortId= question_data['id'],
            subText = question_data['subText'],
            frequency = question_data['frequency'],
            clockTime = question_data['clockTime'],
            clockTime_start = question_data['clockTime_start'],
            clockTime_end = question_data['clockTime_end'],
            nextDayToAnswer = question_data['nextDayToAnswer'],
            category = question_data['category'],
            imageURL = question_data['imageURL'],
            url = question_data['url'],
            questionType  = question_data['questionType'],
            deactivateOnAnswer = question_data['deactivateOnAnswer'],
            deactivateOnDate = question_data['deactivateOnDate'],
            activate_question = question_data['activate_question'],
            deactivate_question = question_data['deActivate_question'],
            activation_condition = question_data['activation_condition'],
            deactivation_condition = question_data['deActivation_condition'],
            clockTime_timezone =  "Europe/Berlin"
        )
        logger.info("create_question_in_db::done::%s",question.id)
        if "answer" in question_data:
            #Create Answer table
            for answer_data in question_data['answer']:
                create_answer_from_file_in_db(question.id,answer_data)
    logger.info("create_survey_in_db::end %s",survey)
    return survey


def create_answer_from_file_in_db(question_id,answer_data):
    '''
    Create New answer from the json fiel in the database
    '''
    logger.info("creating answer %s",answer_data)
    answerModel.objects.create(
        question_id=question_id,
        answerSortId = answer_data['id'],
        text= answer_data['text'],
        answerSubText = answer_data['subText'] if "subText" in answer_data else "N",
        value = answer_data['value'],
        defaultValue = answer_data['defaultValue'],
        stepSize = answer_data['stepSize'],
        minValue = answer_data['minVal'],
        maxValue = answer_data['maxVal'],
        minText = answer_data['minText'],
        maxText = answer_data['maxText']
    )
    logger.info("create_answer_in_db::successful:end")


def create_answer_in_db(question_id,answer_data):
    '''
    Create New answer in the database
    '''
    logger.info("create_answer_in_db:::start %s",answer_data)
    answer_data['answerSortId'] = answer_data['id'] if 'id' in answer_data else answer_data['answerSortId']
    answer_data['answerSubText'] = answer_data['subText'] if "subText" in answer_data else "N"
    answerModel.objects.create(
        question_id = question_id,
        answerSortId = answer_data['answerSortId'],
        text= answer_data['text'],
        answerSubText= answer_data['answerSubText'],
        value = answer_data['value'],
        defaultValue = answer_data['defaultValue'],
        stepSize = answer_data['stepSize'],
        minValue = answer_data['minValue'],
        maxValue = answer_data['maxValue'],
        minText = answer_data['minText'],
        maxText = answer_data['maxText']
    )
    logger.info("create_answer_in_db::successful:end")

def create_question_answers_from_file_in_db(survey_id,question_data):
    '''
    Create New question in the database
    '''
    question = questionModel.objects.create(
            survey_id= survey_id,
            title= question_data['title'],
            active= 1,
            sortId= question_data['id'],
            subText = question_data['subText'],
            frequency = question_data['frequency'],
            clockTime = question_data['clockTime'],
            clockTime_start = question_data['clockTime_start'],
            clockTime_end = question_data['clockTime_end'],
            nextDayToAnswer = question_data['nextDayToAnswer'],
            category = question_data['category'],
            imageURL = question_data['imageURL'],
            url = question_data['url'],
            questionType  = question_data['questionType'],
            deactivateOnAnswer = question_data['deactivateOnAnswer'],
            deactivateOnDate = question_data['deactivateOnDate'],
            activate_question = question_data['activate_question'],
            deactivate_question = question_data['deactivate_question'],
            activation_condition = question_data['activation_condition'],
            deactivation_condition = question_data['deactivation_condition'],
            clockTime_timezone = question_data['clockTime_timezone']
        )
    logger.info("create_question_in_db::done::%s",question.id)
    if "answer" in question_data:
        #Create Answer table
        for answer_data in question_data['answer']:
            create_answer_from_file_in_db(question.id,answer_data)

    logger.info("create_answer_in_db::successful:end")
    return question

def create_question_answers_in_db(survey_id,question_data):
    '''
    Create New question in the database
    '''
    question = questionModel.objects.create(
            survey_id= survey_id,
            title= question_data['title'],
            active= 1,
            sortId= question_data['id'],
            subText = question_data['subText'],
            frequency = question_data['frequency'],
            clockTime = question_data['clockTime'],
            clockTime_start = question_data['clockTime_start'],
            clockTime_end = question_data['clockTime_end'],
            nextDayToAnswer = question_data['nextDayToAnswer'],
            category = question_data['category'],
            imageURL = question_data['imageURL'],
            url = question_data['url'],
            questionType  = question_data['questionType'],
            deactivateOnAnswer = question_data['deactivateOnAnswer'],
            deactivateOnDate = question_data['deactivateOnDate'],
            activate_question = question_data['activate_question'],
            deactivate_question = question_data['deactivate_question'],
            activation_condition = question_data['activation_condition'],
            deactivation_condition = question_data['deactivation_condition'],
            clockTime_timezone = question_data['clockTime_timezone'] 
        )
    logger.info("create_question_in_db::done::%s",question.id)
    if "answer" in question_data:
        #Create Answer table
        for answer_data in question_data['answer']:
            create_answer_in_db(question.id,answer_data)

    logger.info("create_answer_in_db::successful:end")
    return question


def update_study_db_details(form_data):
    """
    Updates study details in the database based on the provided form data.

    Args:
        form_data (dict): A dictionary containing edited study details .

    Updates the study record matching the title with the values in `form_data`.
    """
    survey_id = ""
    if 'survey' in form_data:
        survey_id = form_data['survey']
    studymodel.objects.filter(title=form_data['name']).update(description=form_data['description'],
                    duration=form_data['duration'],
                    numberOfSubjects = form_data['number_of_subjects'],
                    is_test = form_data[constants.field_name_is_test],
                    enrolled_subjects = len(form_data['enrolled_subjects']),
                    passive_monitoring = True if len(form_data[constants.field_name_sensor_list]) >0 else False,
                    frequency = form_data[constants.field_name_frequency],
                    labeling = form_data[constants.field_name_labeling],
                    sensor_list = form_data[constants.field_name_sensor_list],
                    ecological_momentary_assessment = form_data['ema_checkbox'],
                    survey = survey_id)


def assign_all_group_permissions(username, groupname):
    '''
    Assign group for the user with permissions
    '''
    looged_user = User.objects.get(username=username)

    userGroup = Group.objects.get(name=groupname)
    add_permission = Permission.objects.get(name='Can add study')
    change_permission = Permission.objects.get(name='Can change study')
    delete_permission = Permission.objects.get(name='Can delete study')
    view_permission = Permission.objects.get(name='Can view study')

    creator_permissions = [
        add_permission,
        change_permission,
        delete_permission,
        view_permission,
    ]

    userGroup.user_set.add(looged_user)
    userGroup.permissions.set(creator_permissions)


def close_study_model(study_name):
    '''
    Update closed flag for the study
    '''
    studymodel.objects.filter(title=study_name).update(closed=1)

    # logging.info(values)
    return True

def retrieve_all_survey_for_user(user,session_key):
    '''
    retrieve_all_survey_for_user
    '''
    queryset = surveyModel.objects.none()
    group_name = SessionManager.get_specific_session_data(session_key,constants.session_key_groupname,None)
    ema_studies = SessionManager.get_specific_session_data(session_key,constants.session_key_studies_ema,[])

    #get the usergroup
    if "administrator" in group_name:
        queryset = surveyModel.objects.values()
        return json.loads(survey_serializer(queryset))
    return get_list_surveys_for_user(user,ema_studies)
    
    
def update_answer_in_db(form_data,answer_id):
    '''
    update_answer_in_db
    '''
    logger.info("update_answer_in_db ::%s :: %s",form_data,answer_id)
    answerModel.objects.filter(id=answer_id).update(text=form_data["text"],
                                                    answerSubText = form_data['answerSubText'],
                                                    answerSortId = form_data['answerSortId'],
                                                    value=form_data['value'],
                                                    defaultValue = form_data["defaultValue"],
                                                    minValue = form_data["minValue"],
                                                    maxValue = form_data["maxValue"],
                                                    stepSize = form_data["stepSize"],
                                                    maxText = form_data["maxText"],
                                                    minText = form_data["minText"]

                                                )


def delete_answer_in_db(answer_id):
    '''
    delete_answer_in_db
    '''
    answerModel.objects.get(id=answer_id).delete()

def update_question_in_db(question_id,question_data):
    logger.info("update_question_in_db %s",question_data)
    logger.info("update_question_in_db %s",question_data['sortId'])
    if question_data['activate_question'] is None:
        question_data['activate_question'] = []
    if question_data['deactivate_question'] is None:
        question_data['deactivate_question'] = []
    if question_data['clockTime_start'] is None:
        question_data['clockTime_start'] = []
    if question_data['clockTime_end'] is None:
        question_data['clockTime_end'] = []
    
    questionModel.objects.filter(id=question_id).update(title= question_data['title'],
                                                        subText = question_data['subText'],
                                                        active = 1 ,
                                                        sortId = question_data['sortId'],
                                                        frequency = question_data['frequency'],
                                                        clockTime = question_data['clockTime'],
                                                        clockTime_start = question_data['clockTime_start'],
                                                        clockTime_end = question_data['clockTime_end'],
                                                        nextDayToAnswer =question_data['nextDayToAnswer'],
                                                        category = question_data['category'],
                                                        imageURL = question_data['imageURL'],
                                                        url = question_data['url'],
                                                        questionType = question_data['questionType'],
                                                        deactivateOnAnswer = question_data['deactivateOnAnswer'],
                                                        deactivateOnDate = question_data['deactivateOnDate'],
                                                        activate_question = question_data['activate_question'],
                                                        deactivate_question = question_data['deactivate_question'],
                                                        activation_condition = question_data['activation_condition'],
                                                        deactivation_condition = question_data['deactivation_condition'],
                                                        clockTime_timezone =  "Europe/Berlin"
                                                            )


def delete_survey_for_user(groupName,user,survey_id):
    '''
    update_question_in_db
    '''
    if "administrator" in groupName:
        result = surveyModel.objects.filter(id=survey_id).all()
    else:  
        result = surveyModel.objects.filter(owner=user).filter(id=survey_id).all()
    # if the user belong to Investigator or viewer groups
    result.delete()
    return True

def delete_question_from_db(question_id: int, survey_id: int) -> bool:
    """
    Delete a question within a survey and shift subsequent sortIds up by 1
    so they remain contiguous (1..N).
    """
    with transaction.atomic():
        try:
            q = (questionModel.objects
                 .select_for_update()
                 .get(id=question_id, survey_id=survey_id))
        except questionModel.DoesNotExist:
            return False

        removed_pos = q.sortId
        q.delete()

        # Shift everything after the removed position up by 1
        (questionModel.objects
         .filter(survey_id=survey_id, sortId__gt=removed_pos)
         .update(sortId=F('sortId') - 1))

    return True

def retrieve_all_questions_for_survey(survey_id):
    #retrieve survey based on group permission
    queryset = questionModel.objects.filter(survey__pk=survey_id).values()
    question_list = json.loads(question_db_serializer(queryset))
    for question in question_list:
        # Retrieve and print answers for the current question
        answers = answerModel.objects.filter(question_id= question["db_id"]).values()
        question["answer"] = json.loads(answer_serializer(answers))
    sorted_questions_list = json.dumps(sorted(question_list, key=itemgetter('id')))
    return json.loads(sorted_questions_list)



def retrieve_download_questions_for_survey(survey_id):
    '''
    update_question_in_db
    '''
    #retrieve survey based on group permission
    queryset = questionModel.objects.filter(survey__pk=survey_id).values()
    #logger.info("retrieve_all_questions_for_survey:::%s",queryset)
    question_list = json.loads(question_serializer(queryset))
    for question in question_list:
        # Retrieve and print answers for the current question
        answers = answerModel.objects.filter(question_id= question["db_id"]).values()
        question["answer"] = json.loads(answer_download_serializer(answers))
    
    sorted_questions_list = json.dumps(sorted(question_list, key=itemgetter('id')))
    return json.loads(sorted_questions_list)


def retrieve_all_answers_for_questions(question_id):
    '''
    update_question_in_db
    '''
    # Retrieve and print answers for the current question
    answers = answerModel.objects.filter(question_id= question_id).values()
    return json.loads(answer_serializer(answers))

def retrieve_all_categories_for_survey(survey_id):
    '''
    retrive category list
    '''

    queryset = categoryModel.objects.filter(survey__pk=survey_id).order_by('categoryValue').values()
    category_list = json.loads(category_serializer(queryset))
    logger.info("retrieve_all_categories_for_survey %s",category_list)
    return category_list


def retrieve_survey(survey_id):
    '''
    update_question_in_db
    '''
    return surveyModel.objects.get(id=survey_id)

def retrieve_question(question_id):
    '''
    update_question_in_db
    '''
    return questionModel.objects.get(id=question_id)

def retrieve_survey_details(survey_id):
    '''
    update_question_in_db
    '''
    data = surveyModel.objects.filter(id=survey_id).values()
    return  json.loads(survey_serializer(data))[0]

def retrieve_question_details(question_id):
    '''
    update_question_in_db
    '''
    data = questionModel.objects.filter(id=question_id).values()
    question_json = json.loads(question_db_serializer(data))[0]

    logger.info("retrieve_question_details:::%s",question_json)
    question_json["answer"] = retrieve_all_answers_for_questions(question_id)
    for answer in question_json["answer"]:
        answer["answerSortId"] = answer["id"]
    return  question_json

def retrieve_questions_greater_than_sortId(survey_id,sort_id):
    questions = questionModel.objects.filter(survey_id=survey_id, sortId__gt=sort_id).values()
    question_json = json.loads(question_serializer(questions))
    logger.info("retrieve_questions_greater_than_sortId:::%s",question_json)
    return question_json

def add_verification_code(code,token):
    '''
   add_verification_code
    '''
    downloadFile.objects.filter(token=token).update(code=code)
    return True

def retrieve_all_survey_for_user(user,session_key):
    queryset = surveyModel.objects.none()
    groupName = SessionManager.get_specific_session_data(session_key,constants.session_key_groupname,None)
    ema_studies = SessionManager.get_specific_session_data(session_key,constants.session_key_studies_ema,[])

    #get the usergroup
    if "administrator" in groupName:
        queryset = surveyModel.objects.values()
        survey_list = json.loads(survey_serializer(queryset))        
        for obj in survey_list:
            study_details = studymodel.objects.filter(survey=obj['id']).values() 
            if study_details:
                obj["study_name"] = ", ".join([s["title"] for s in study_details])
        return survey_list
    else :
        return get_list_surveys_for_user(user,ema_studies)


def get_list_surveys_for_user(user,ema_studies):
    '''
    get_list_surveys_for_user
    
    '''
    # Use a set to track unique survey IDs
    unique_surveys = set()
    surveys = []
    queryset = surveyModel.objects.filter(owner=user).values()
    if queryset:
        for survey in json.loads( survey_serializer(queryset)):
            study_details = studymodel.objects.filter(survey=survey['id']).values() 
            if study_details:
                survey["study_name"] = ", ".join([s["title"] for s in study_details]) 
            # Check if the survey ID is not already in the set
            if survey['id'] not in unique_surveys:
                unique_surveys.add(survey['id'])
                surveys.append(survey)
    # get all ema study groups and the attached surveys
    for studyname in ema_studies: 
        data = studymodel.objects.filter(title=studyname).values()
        jsondata = json.loads(custom_serializer(data))[0]
        survey = surveyModel.objects.filter(id = jsondata["survey"]).values()
        if survey:
            for survey in json.loads(survey_serializer(survey)):
                survey['study_name'] = jsondata["title"]
                # Again, check for duplicates before adding
                if survey['id'] not in unique_surveys:
                    unique_surveys.add(survey['id'])
                    surveys.append(survey)

    return surveys

def generete_survey_notification_obj(survey,study_duration):
    '''
    generete_survey_notification_obj
    '''
    days_obj ={}
    for quest in survey["questions"]:

        unique_clock_times = set()
        start = 0
        if "startOnDay" in quest:
            start = quest["startOnDay"]
        #if "nextDayToAnswer" in quest and quest["nextDayToAnswer"] is not None:
        #   start = quest["nextDayToAnswer"]
        end = study_duration
        if "endOnDay" in quest:
            end = quest["endOnDay"]
        if "deactivateOnDate" in quest:
            if quest["deactivateOnDate"] is not None and quest["deactivateOnDate"] != 0:
                end = quest["deactivateOnDate"]
        if quest["frequency"] != 0:
            end += 1  # Adjust end to ensure the loop runs at least once
            for i in range(start,end,quest["frequency"]):
                if "clockTime" in quest:
                    unique_clock_times.add(quest['clockTime'])
                days_obj[i] = sorted(list(unique_clock_times))

def get_categories_from_db(survey_id):
    '''
    retreive  list of categories of a survey
    '''
    categories_list = categoryModel.objects.filter(survey_id=survey_id)
    logger.debug("get_categories_from_db::successful:end")
    return categories_list

def create_categories_in_db(survey_id,category_data):
    '''
    Create new categories for a survey in the database
    '''
    logger.info("create_categories_in_db:::start %s",category_data)
    for data in category_data['category_list']:
        categoryModel.objects.create(
            survey_id = survey_id,
            categoryValue = int(data['categoryValue']),
            categoryTitle= data['categoryTitle'],
            didSubjectAsk= data['didSubjectAsk']
        )
    logger.info("create_categories_in_db::successful:end")

def create_categories_in_db_from_data(survey_id,category_data):
    '''
    Create new categories for a survey in the database
    '''
    for data in category_data:
        categoryModel.objects.create(
            survey_id = survey_id,
            categoryValue = int(data['categoryValue']),
            categoryTitle= data['categoryTitle'],
            didSubjectAsk= data['didSubjectAsk']
        )
    logger.info("create_categories_in_db::successful:end")

def retrieve_test_cases_for_study(study_name):

    study = studymodel.objects.filter(title=study_name).values()
    results = qctestsModel.objects.filter(study_id=study[0]["id"]).values()

    return json.dumps(list(results), default=str)

def update_test_case_flags(testcase_updates,username):
    """
    Retrieve a test case by its ID and update the tested_by_admin and tested_by_owner flags.

    Args:
        testcase_id (str): The unique ID of the test case to retrieve.
        tested_by_admin (bool, optional): New value for the tested_by_admin field.
        tested_by_owner (bool, optional): New value for the tested_by_owner field.

    Returns:
        str: Success or error message.
    """
    success_count = 0
    failure_count = 0
    errors = []
    logger.info(type(testcase_updates))
    # Iterate over the provided updates
    for test_case in testcase_updates:
        try:
            logger.info("An test",test_case,type(test_case))
            # Retrieve the test case
            db_test_case = qctestsModel.objects.get(id=test_case['id'])
            db_test_case.tested_by_admin = test_case.get('tested_by_admin', db_test_case.tested_by_admin)
            db_test_case.tested_by_owner = test_case.get('tested_by_owner', db_test_case.tested_by_owner)
            db_test_case.admin_username = username
            # Save the updated object to the database
            db_test_case.save()

            success_count += 1

        except Exception as e:
            logger.info("An error occurred while updating Test Case %s: %s",test_case['id'],e)
            failure_count += 1
    return {
        "success_count": success_count,
        "failure_count": failure_count,
        "errors": errors,
    }

def retrieve_study_details_by_title(study_name):
    '''
    retrieve_study_details_by_title     
    '''
    # Retrieve study details based on the title
    study = studymodel.objects.filter(title=study_name).values()   
    return json.dumps(study[0], default=str)


def get_question_by_sortid(survey_id, sort_id):
    '''
    Retrieve a question from the database based on the given survey ID and sort ID.
    Args:
        survey_id (int): The ID of the survey to which the question belongs.
        sort_id (int): The sort ID of the question within the survey.
    Returns:
        dict or None: A dictionary representing the question if found, or None if no matching question exists.

    '''
    # Retrieve question based on survey id and sort id
    question = (questionModel.objects
                .filter(survey_id=survey_id, sortId=sort_id)
                .values())
    if question:
        result = json.loads(question_db_serializer(question))[0]
        logger.info("get_question_by_sortid::question: %s", result)
        return result
    return None
