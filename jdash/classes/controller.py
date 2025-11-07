import os, threading
import csv
import os, logging , json
import subprocess
from django.db import transaction
from django.urls import reverse
from django.forms.formsets import formset_factory     
from django.http.response import HttpResponse
from datetime import datetime, timedelta
from django.utils.encoding import escape_uri_path
from jdash.textmessages import TextMessages as textmessages
from jdash.classes.survey import Survey,check_and_enter_answer_in_db , update_answer_choice_text_details
from jdash.classes.survey import update_sortid_of_questions,check_question_type_change
from jdash.classes.datahelper import get_study_form_data , get_question_form_data, get_blank_answer_object
from jdash.forms import  SurveyForm, DeleteSubjectForm, SendNotificationForm
from jdash.forms import RemoveSubjectsForm, CreateSubjectForm, QuestionForm, AnswerForm
from jdash.classes.study import get_all_study_details, create_study 
from jdash.classes.study import zip_unused_sheets , save_study_json, open_study_json 
from jdash.classes.fileutils import get_json_data, change_permissions
from jdash.classes.fileutils import delete_user_files, get_notification_json_for_study
from jdash.classes.study import update_study_details
from jdash.classes.subject import create_subjects_for_study, remove_subjects_for_study, count_number_of_subject_pdf
from jdash.classes.notification import send_push_notification
from jdash.apps import jdashConfig as config
from jdash.apps import constants as constants
from jdash.models import FileDownloadToken
from jdash.interface.session_manager import SessionManager
from jdash.classes.fileutils import get_json_data,get_notification_json_for_study
from jdash.classes.utils import modify_questions_list_to_string
from jdash.classes.utils import normalize_question_data_defaults
from jdash.classes.dbutils import retrieve_question,get_question_by_sortid,delete_answer_in_db
from jdash.classes.dbutils import  update_study_db_details, create_question_answers_in_db,retrieve_question_details
from jdash.classes.dbutils import retrieve_all_categories_for_survey,retrieve_all_answers_for_questions,create_categories_in_db_from_data
from jdash.classes.dbutils import   retrieve_all_questions_for_survey, delete_question_from_db, retrieve_all_survey_for_user
from jdash.classes.dbutils import update_question_in_db,create_new_survey_in_db,retrieve_survey_details,create_survey_in_db
from jdash.classes.dbutils import get_categories_from_db,retrieve_test_cases_for_study,update_survey_info_in_db
from jdash.classes.dbutils import retrieve_study_details_by_title
from jdash.classes.datahelper import   get_answer_form_data,get_question_form_data,get_category_form_data
from jdash.classes.datahelper import get_study_form_data , get_question_form_data
from jdash.classes.datahelper import get_help_texts_for_category_form,get_help_texts_for_question_form 
from jdash.classes.datahelper import get_help_texts_for_survey_form
from jdash.classes.notification import send_push_notification
from jdash.forms import  SurveyForm, DeleteSubjectForm, SendNotificationForm, CategoryForm
from jdash.forms import RemoveSubjectsForm, CreateSubjectForm, QuestionForm, JSONUploadForm, AnswerForm
from jdash.classes.study import get_all_study_details, create_study 
from jdash.classes.study import zip_unused_sheets , save_study_json, open_study_json 
from jdash.classes.subject import create_subjects_for_study, remove_subjects_for_study, count_number_of_subject_pdf
from jdash.classes.survey import Survey,check_and_enter_answer_in_db , update_answer_choice_text_details, update_other_answer_details
from jdash.classes.survey import update_sortid_of_questions
from jdash.classes.survey import process_category_data


logger = logging.getLogger("django")

def dowload_unused_qr_code_files(study_name):

    zip_unused_sheets(study_name)       
    # Define the full file path
    filepath = os.path.join(config.dash_folder, os.path.join(config.app_study_folder, study_name, config.zip_file))
    # Open the file for reading content
    with open(filepath, 'rb') as fh:
        # Set the return value of the HttpResponse
        response = HttpResponse(fh.read(), content_type=constants.zip_content_type)
        # Set the HTTP header for sending to browser
        response['Content-Disposition'] = f"attachment; filename*=utf-8''{escape_uri_path(config.zip_file)}"
        # Return the response value
        return response
    

def download_subject_qr_file(subject_id):
    study_name = subject_id.split(".")[0]
    filepath = os.path.join(config.dash_folder, os.path.join(config.app_study_folder, study_name_user_id(study_name),  config.sheets_folder , subject_id+constants.pdf_extension))
    with open(filepath, 'rb') as fh:
        # Set the return value of the HttpResponse
        response = HttpResponse(fh.read(), content_type=constants.pdf_content_type)
        # Set the HTTP header for sending to browser
        response['Content-Disposition'] = "attachment; filename=%s" %subject_id+constants.pdf_extension
        # Return the response value
        return response
    
def study_name_user_id(value):
    bufferdString = ""
    strArray = value.split(constants.underscore_seperator)
    #check for last occurence of _ and get the study name
    for i in range(len(strArray) -1):
        bufferdString = bufferdString + strArray[i] 
        bufferdString = bufferdString + constants.underscore_seperator
    return bufferdString[:-1]             
    
def download_dataset(study_dataset_name):   
    logger.info("dowload_dataset")    
    # Define the full file path
    filepath = os.path.join(config.storage_folder, os.path.join(config.download_folder, study_dataset_name + constants.zip_extension))
    # Open the file for reading content
    with open(filepath, 'rb') as fh:
        # Set the return value of the HttpResponse
        response = HttpResponse(fh.read(), content_type=constants.zip_content_type)
        # Set the HTTP header for sending to browser
        response['Content-Disposition'] = f"attachment; filename*=utf-8''{escape_uri_path( study_dataset_name + constants.zip_extension)}"
        return response
    
def initiate_download_study_dataset(study_name,data_type,user_details):
    ''' Method to initiate download study 
    Return zip file to downlaod
    '''
    file_date_identifier = datetime.strftime(datetime.now().astimezone(),'%Y-%m-%dT%H:%M:%S')
    # Build the SSH command to execute the remote script
    ssh_command = f"ssh {config.remote_username}@{config.juseless_server} 'python3 {config.juseless_download_script_path} {study_name} {data_type} {file_date_identifier}'"        
    executable_filepath = os.path.join(config.storage_folder,config.download_folder,"download_dataset.sh")
    try:
        change_permissions(executable_filepath)
        if not os.path.exists(executable_filepath):
            f = open(executable_filepath, 'x',encoding='utf-8')
        
        with open(executable_filepath, 'a',encoding='utf-8') as jf:
                jf.write(ssh_command)
                jf.write("\n")

                jf.close()

        filename = study_name+"_"+data_type+"_"+ file_date_identifier

         # Start the check and email process in a new thread
        thread = threading.Thread(target=check_file_and_send_email, args=(user_details, filename,))
        thread.start()   
        return True   
    except Exception as e:
        logger.info("An error occurred: %s",e)
        return False
    

def check_file_and_send_email(user_details,filename):
    zip_filepath = os.path.join(config.storage_folder,config.download_folder,filename+".zip")

    token_instance = FileDownloadToken.objects.create(
        first_name= user_details.get('first_name'),
        email = user_details.get('email'),
        file_name=filename,
        status='initiated',
        expiration_date=datetime.now().astimezone() + timedelta(days=7)  # Link expires in 1 week
    )
    link = "https://jdash.inm7.de" + reverse('download_dataset',args=[token_instance.token])
    # After generating the link
    token_instance.link = link
    token_instance.save()
    csv_filepath = os.path.join(config.storage_folder,config.download_folder,config.download_zip_files_log)
    change_permissions(csv_filepath)
    new_row = [filename,user_details.get('first_name'),user_details.get('email'),link,'initiated',datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"),'','']
    # Check if the file exists to decide on writing the header
    file_exists = os.path.isfile(csv_filepath)
    with open(csv_filepath, mode='a', newline='',encoding='utf-8') as file:
        writer = csv.writer(file)
        # If the file does not exist, write the header first
        if not file_exists:
            writer.writerow(['Dataset','FirstName', 'Email', 'Link',  'Status', 'Requested','Emailed','Downloaded'])

            # Write the data row
            writer.writerow(new_row)

            
            
def generate_csv_files(study_name,version):
    # Build the SSH command to execute the remote script
    ssh_command = [
        "ssh",
        f"{config.remote_username}@{config.juseless_server}",
        f"/usr/bin/python3 {config.juseless_analysis_csv_files_script_path} {study_name} {version}"        
    ]
    try:
        # Execute the SSH command
        subprocess.run(ssh_command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        logger.info(f"Command failed with error: {e}")
    except Exception as e:
        logger.info(f"An error occurred: {e}")
    return 0   

def get_survey_list(session_key):
    ''' Method to return all survey list for the user'''
    total_list = []
    try:
        ema_studies = SessionManager.get_specific_session_data(session_key,constants.session_key_old_ema)
        if ema_studies :
            for study in ema_studies:
                data = get_json_data(study)
                survey={}
                survey['id'] = '999'
                survey[constants.key_name_study_title] = study
                survey[constants.key_name_study_name] = data[constants.key_study_name_json]
                survey[constants.key_name_survey_description] = study+" json file"
                if constants.key_name_survey_topN not in data[constants.key_name_survey]:
                    survey[constants.key_name_survey_topN] = -1
                else:
                    survey[constants.key_name_survey_topN] = data[constants.key_name_survey][constants.key_name_survey_topN]
                total_list.append(survey) 
            return total_list
    except Exception as e:
        logger.info("Exception occured while fetching from survey files: %s",e)
        return "Unknown Exception occured"

def download_ics_file(study_name,subject_id):
    """
    Generates and downloads an ICS (iCalendar) file containing scheduled events for a given study and subject.

    Args:
        study_name (str): The name of the study for which the schedule is being generated.
        subject_id (str): The unique identifier for the subject.

    Returns:
        HttpResponse: A response containing the ICS file as an attachment, or an error message with status 400
                        if the schedule is invalid or missing.

    Raises:
        ValueError: If the schedule contains non-integer keys for days.

    """
    output_path = os.path.join(config.users_folder, subject_id + ".ics")
    duration_minutes = 30
    summary = "Jtrack Notification"
    tz = constants.timezone
    schedule = get_notification_json_for_study(study_name)
    if not schedule or 'days' not in schedule:
        return HttpResponse(f'Schedule key {study_name!r} missing or invalid', status=400)

    days_map = schedule['days']
    start_date = datetime.now().astimezone()
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
    # 2. Prepare calendar
    cal = Calendar()
    cal.add('prodid', '-//Jtrack//EN')
    cal.add('version', '2.0')
    for offset_str, minutes_list in days_map.items():
        try:
            offset = int(offset_str)
        except ValueError:
            continue  # skip non‐integer keys
        event_date = start_date + timedelta(days=offset)

        for minutes in minutes_list:
            hour = minutes // 60
            minute = minutes % 60

            dtstart = tz.localize(
                datetime(
                    year=event_date.year,
                    month=event_date.month,
                    day=event_date.day,
                    hour=hour,
                    minute=minute,
                )
            )

            ev = Event()
            ev.add("summary", summary or study_name)
            ev.add("dtstart", dtstart)
            ev.add("dtend", dtstart + timedelta(minutes=duration_minutes))
            cal.add_component(ev)

    # 6) Write .ics
    with open(output_path, "wb") as out:
        out.write(cal.to_ical())

    logger.info("Written %s with %s events.",output_path,len(cal.subcomponents))
    # Open the file for reading content
    with open(output_path, 'rb') as fh:
        # Set the return value of the HttpResponse
        response = HttpResponse(fh.read(), content_type=constants.ics_content_type)
        # Set the HTTP header for sending to browser
        response['Content-Disposition'] = "attachment; filename=%s" %study_name+constants.ics_extension
        return response

def get_all_survey_details(user,session_key):
    context = {}
    survey_list_details = []
    try:
        survey_from_db = retrieve_all_survey_for_user(user,session_key)
        if len(survey_from_db) > 0 :
            for survey in survey_from_db:
                survey_list_details.append(survey)
        #combine details from both database and ema study.json file
        survey_files_list =  get_survey_list(session_key)
        logger.info("survey_files_list %s",survey_files_list)
        if survey_files_list != None:
            for survey in survey_files_list:
                survey_list_details.append(survey)
        context = context_for_survey_list_page()
        context["survey_list"] = survey_list_details
    except Exception as e:
        logger.info("Exception occured while fecthing surveys %s",e)
        context[constants.key_name_error_message] = "get_all_survey_details:: Exception occured"
    return context


def create_question_answer_for_survey(survey_id,form,answer_form):
    '''
    create_question_answer_for_survey
    '''
    logger.info("create_question_answer_for_survey %s",survey_id)
    question_obj =  get_question_form_data(form)
    question_obj['id'] = question_obj['sortId']
    question = create_question_answers_in_db(survey_id,normalize_question_data_defaults(question_obj))
    question_id = question.pk
    logger.info("question %s has been succesfully created in db",question_id)
    #check for duplicate sortIds  
    #get the question Id with the same sortId and update same and the sortId of all questions accordingly
    #duplicate_sortId_question = get_question_by_sortid(question_id,question.survey_id,question.sortId)
    #if duplicate_sortId_question is not None :
        #update_sortid_of_questions(duplicate_sortId_question["db_id"],duplicate_sortId_question["sortId"] + 1)
        #logger.info("no ::update_sortid_of_questions::%s",question_id )
    if answer_form.is_valid():
        form_data = get_answer_form_data(answer_form)
        logger.info("storing  answer data %s",form_data['answers'])
        check_and_enter_answer_in_db(question_id,form_data['answers'])
    return context_for_create_survey_page(survey_id)


def update_question_answer_for_survey(question_id,form,answer_id_list,answer_formset):
    """
    update a question answer of survey
    :param question_id,form
    :param answer_form
    update both question and answer tables
    :return:
    """
    question_obj =  get_question_form_data(form)
    # update the question sortId first and then other details
    update_sortid_of_questions(question_id,question_obj["sortId"])
    qtype = int(question_obj["questionType"])
    flag = check_question_type_change(question_id, question_obj)
    with transaction.atomic():
        logger.info('questionid ::%s:: with :: %s updating in db', question_id, question_obj)
        update_question_in_db(question_id, question_obj)
        logger.info('completed updated %s', question_id)
        # Branch by direction
        if flag == +1:
            # choice (1/2) -> other (0 or >=3)
            for aid in (answer_id_list or []):
                delete_answer_in_db(aid)
            # Insert a blank/default answer structure for "other" types
            check_and_enter_answer_in_db(question_id, get_blank_answer_object())           

        if flag == -1:
            # other (0 or >=3) -> choice (1/2)
            for aid in (answer_id_list or []):
                delete_answer_in_db(aid)
            if answer_formset.is_valid():
                form_data = get_answer_form_data(answer_formset)
                logger.info("storing answer data (choice) %s", form_data.get('answers'))
                # Insert new choice answers from form
                check_and_enter_answer_in_db(question_id, form_data['answers'])
            else:
                logger.warning("answer_formset invalid: %s", getattr(answer_formset, "errors", None))
        # flag == 0 → same group; update answers in place if provided
        if answer_formset.is_valid():
            form_data = get_answer_form_data(answer_formset)
            answers = form_data.get('answers', [])
            logger.info("answer_id_list: %s", answer_id_list)
            logger.info("incoming answers: %s", answers)

            if answer_id_list:
                # Update existing answers
                if qtype in (1, 2):  # choice group
                    update_answer_choice_text_details(question_id, answers, answer_id_list)
                else:                # "other" group (0 or >=3)
                    update_other_answer_details(question_id, answers, answer_id_list)
            else:
                # No existing answers → insert
                check_and_enter_answer_in_db(question_id, answers)
                logger.info("check_and_enter_answer_in_db %s", question_id)
        else:
            logger.warning("answer_formset invalid: %s", getattr(answer_formset, "errors", None))

    # get the survey_id from the question_db_object
    context = context_for_create_survey_page(retrieve_question(question_id).survey_id)
    logger.info('update_question_answer_for_survey::: %s', context['survey_id'])
    return context



def update_survey_details(study_name,values_to_be_updated):
    """
    update a study (values to study.json file)
    :param study_name:
    :param values_obj:
    update both question and answer tables
    :return:
    """
    study_json = open_study_json(study_name)
    # Update a question
    question_id = values_to_be_updated['id']  # Example: the first question
    Survey.update_question(question_id, title="Updated Question Title", sub_text="New subtext")

    # Update an answer for the question
    answer_index_to_update = 1  # Example: the second answer of the first question
    Survey.update_answer(question_id, answer_index_to_update, answer_text="Updated Answer Text", answer_value=3.14)

    # Convert to JSON for storage or further processing
    updated_survey_json = Survey.to_json()

    save_study_json(study_name, updated_survey_json)
    return True

def create_survey_from_surveyForm(form_data,user):
    """
    create a survey in the database
    :param
    survey_name: name of the survey
    survey_dict: survey details
    user: user object
    :return:
    """
        
    survey = create_new_survey_in_db(form_data,user)
        
    return context_for_create_survey_page(survey.id)

def update_survey_from_surveyForm(form_data,survey_id):
    """
    create a survey in the database
    :param
    survey_name: name of the survey
    survey_dict: survey details
    user: user object
    :return:
    """
        
    survey = update_survey_info_in_db(form_data,survey_id)
        
    return context_for_create_survey_page(survey.id)

def upload_survey_json_file(survey_str,user):
    survey_dict = {}
    formatted_date = datetime.strftime(datetime.now().astimezone(),'%Y-%m-%dT%H:%M:%S')
    survey_id = 0
    survey_dict['survey'] = json.loads(survey_str)
    survey = create_survey_in_db("survey_"+formatted_date,survey_dict['survey'] ,user)
    survey_id = survey.id
    return context_for_create_survey_page(survey_id)

def delete_question_from_survey(question_id,survey_id):
    """
    update a study (values to study.json file)
    :param study_name:
    :param values_obj:
    update both question and answer tables
    :return:
    """
    logger.info("delete_question_from_survey %s",question_id)
    delete_question_from_db(question_id,survey_id)
    return context_for_create_survey_page(survey_id)

def delete_question_from_file(study_name,title):
    """
    update a study (values to study.json file)
    :param study_name:
    :param values_obj:
    update both question and answer tables
    :return:
    """
    study_json = open_study_json(study_name)
    question_list = study_json["survey"]["questions"]
    for question in question_list:
        if question['title'] == title:
            question_list.remove(question)
    return study_json

def update_row_order(oldOrder,newOrder):
    """
    update a study (values to study.json file)
    :param study_name:
    :param values_obj:
    update both question and answer tables
    :return:
    """
    

    return True


def delete_subjects_from_server(study_name,subject_ids):
    """
    This method is to serve the delete request of the subjects
    params : subject id list
    
    This method is used to created  text file with all the subjects id per day
    This text file is then used to run a batch processing to delete the data on juseless server
    Can ask to create  a shared folder to access for the serves or a link 
    """
    logger.info("delete_subjects_from_server subject  :start")
    for subject_id in subject_ids.split(constants.value_sep):        
        subject_id = subject_id.strip()
        if not subject_id:
            logger.info("Skipped empty subject_id")
            continue
        logger.info("delete_subjects_from_server subject_id %s", subject_id)
        delete_user_files(study_name,subject_id)
    logger.info("delete_subjects_from_server subject  :end")

def create_new_study(form,formset,request):
    """
    This method is to serve the create new study
    params : study form
    
    """
    logger.info("add_study:start ")
    context = {}
    form_data = get_study_form_data(form, formset, request)
    logger.info("successful retrieval of form data %s",form_data)
    if form_data[constants.field_name_images] is True:
        handle_uploaded_file(request.FILES[constants.field_name_images_zip_file],
                                form_data[constants.field_name_name])
    response, error = create_study(form_data, request.user)

    logger.info("response after creating entries in db %s",response)
    if response:
        context[constants.key_name_study_meta], context[constants.key_name_stats],context[constants.key_name_error_message] = get_all_study_details(
            request.user)
        
        context[constants.key_name_success_message] = form_data[constants.field_name_name] + "is succesfully created"

    else:
        context[constants.key_name_error_message] = error

    return  context



def update_study_meta_data(study_name,form,formset,request):
    """
    This method is to serve the update meta data of the study
    params : study_name,form,formset,request  
    """
    context = {}
    values_to_be_updated = get_study_form_data(form, formset, request)

    update_study_details(study_name, values_to_be_updated)
    # update database also .. task list is not  yet stored in db
    update_study_db_details(values_to_be_updated)
    # trigger script in the server to update json for ema studies
    # arguments for the script is the study name
    
    with open(config.update_notification_log_file, "w", encoding= "utf-8") as log:
        try:
            execute_command = [
            "python3",
            f"{config.update_json_survey_script_path}",
            f"{study_name}"
            ]
            # Run the script and capture the output
            result = subprocess.run(execute_command, stderr=log,stdout=log, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.info("Error occurred while running the script: %s",e)

    context[constants.key_name_study_meta], context[constants.key_name_stats],error = get_all_study_details(
                    request.user)
    return context

def remove_subjects_from_study(study_name,subject_to_remove,context):
    """
    This method is to serve the delete request of the subjects
    params : subject id list
    
    This method is used to created  text file with all the subjects id per day
    This text file is then used to run a batch processing to delete the data on juseless server
    Can ask to create  a shared folder to access for the serves or a link 
    """
    logger.info("remove_subjects_from_study:start")
    subject_id_with_modality = str(subject_to_remove).split(constants.value_sep)[0]
    (subject_id, app) = str(subject_id_with_modality).split(constants.sep)
    for obj in context['d'][subject_id[:-2]]:
        if obj[constants.key_name_subject_name] == subject_id and obj[constants.key_name_app] == app:
            obj[constants.key_name_status_code] = 3
    id_list = context[constants.key_name_subject_details][constants.key_name_ids_to_be_removed]
    id_list.remove(subject_to_remove)
    context[constants.key_name_subject_details][constants.key_name_ids_to_be_removed] = id_list
    # service will update the csv
    remove_subjects_for_study(study_name, subject_id_with_modality)
    context[constants.key_name_success_message] = subject_id + " has been succesfully removed"
    logger.info("remove_subjects_from_study:end")
    return context

def create_subjects_for_study(study_name,count):
    """
    create subjects for study
    """
    logger.info("create_subjects:start")
    context = {}
    
    context[constants.key_name_meta_data][
        constants.key_name_number_of_subjects] = create_subjects_for_study(study_name, count)
    save_study_json(study_name, context[constants.key_name_meta_data])
    # send message to show in frontend
    context[constants.key_name_success_message] = str(count) + textmessages.success_new_user
    logger.info("create_subjects:end")

def send_push_notification(study_name,message_title,message_text,receivers):
    logger.info("send_notification ::start")
    context = {}
    errors = send_push_notification(message_title, message_text, receivers, study_name)
    if len(errors) == 0:
        context[constants.key_name_success_message] = textmessages.success_notification
    logger.info("send_notification ::end")
    return context 
    

def handle_uploaded_file(f, name):
    """
    Method for handling file upload

    """
    with open(config.images_folder + name + constants.zip_extension, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)



def update_categories_for_survey(survey_id,collect_flag,category_formset):
    """
    create categories for the surveys
    param: survey_id,form
    return: context
    """
    context = {}
    category_data = get_category_form_data(category_formset)
    for category in category_data['category_list']:
        category['didSubjectAsk'] = collect_flag
    logger.info("update_categories_for_survey: category_data %s",category_data)
    exisiting_categories = get_categories_from_db(survey_id)
    logger.info("update_categories_for_survey: exisiting_categories %s",exisiting_categories)
    # find the difference new vs old and updated categories and store in db
    process_category_data(category_data['category_list'],exisiting_categories,survey_id)    
    context = context_for_create_survey_page(survey_id)
    return context


def duplicate_and_create_new_survey_id(source_survey_id,user,session_key):
    '''
    Retrieve the details of the source survey
    Duplicate the survey data and create a new survey with a new ID
    Duplicate the question/categories/answer data 
    '''
    survey_details = retrieve_survey_details(source_survey_id)
    questions = retrieve_all_questions_for_survey(source_survey_id)
    categories = retrieve_all_categories_for_survey(source_survey_id)
    new_survey = create_new_survey_in_db(survey_details,user)
    logger.info("New survey with id %s has been created",new_survey.id)

    for question_data in questions:
        create_question_answers_in_db(new_survey.id,question_data)
    if len(categories) > 0:
        create_categories_in_db_from_data(new_survey.id,categories)
    context = get_all_survey_details(user,session_key)    
    return context

def duplicate_and_create_new_question_id(survey_id,source_question_id):
    '''
    Retrieve the details of the question from source_question_id
    Duplicate the question/answer data  
    Increment the sortId and update all other sortId
    '''
    questions_of_survey = retrieve_all_questions_for_survey(survey_id)
    question_data = retrieve_question_details(source_question_id)
    question_data['id'] = len(questions_of_survey) + 1
    question =  create_question_answers_in_db(survey_id,question_data)
    #new_sequence_id = len(questions_of_survey) + 1
    #update_sortid_of_questions(question.id,new_sequence_id)

    return context_for_create_survey_page(survey_id)



def create_display_sop_list_of_study(study_name):
    """
    This method is to create and return sops dict list
    params : study_name
    """
    context = {}

    context["test_list"] = json.loads(retrieve_test_cases_for_study(study_name))
    #if no sop list is present then send list with study json for the reverseMatch 
    #if len(context["test_list"]) == 0:
    context["study"] = json.loads(retrieve_study_details_by_title(study_name))
    return context


def update_study_meta_data(study_name,form,formset,request):
    """
    This method is to serve the update meta data of the study
    params : study_name,form,formset,request
    """
    context = {}
    error = ""
    values_to_be_updated = get_study_form_data(form, formset, request)
    update_study_details(study_name, values_to_be_updated)
    # update database also
    update_study_db_details(values_to_be_updated)

    #trigger script in the server to generate json for ema studies
    # arguments for the script is the study name
    with open(config.update_notification_log_file, "w") as log:
        try:
            execute_command = [
                "python3",
                f"{config.update_json_survey_script_path}" ,
                f"{study_name}"
            ]
            # Run the script and capture the output
            result = subprocess.run(execute_command, stdout=log,stderr=log, text=True, check=True)
            logger.info("Script Output",result.stdout)
        except subprocess.CalledProcessError as e:
            logger.info("Error occurred while running the script: %s",e)

    context[constants.key_name_study_meta], context[constants.key_name_stats],error = get_all_study_details(
                    request.user)
    return context


#### dont delete these methods
def context_for_home_page(user):
    """
    Generate the context for rendering the home page.

    Args:
        user: The user object for whom the context is being generated.

    Returns:
        dict: A dictionary containing:
            - study_meta: Metadata related to studies associated with the user.
            - stats: Statistical data related to the user's studies.
            - error_message: An error message, if any issue occurs while fetching the data.
    """
    context = {}
    study_meta, stats,error_message = get_all_study_details(user)
    context[constants.key_name_study_meta] = study_meta
    context[constants.key_name_stats] = stats
    context[constants.key_name_error_message] = error_message
    return context

def context_for_study_detail_page(study_name,session_key):
    """
    Generate the context for rendering the study detail page.

    Args:
        study_name (str): The name of the study for which details are being generated.
        session_key (str): The session key to retrieve user-specific session data.

    Returns:
        dict: A dictionary containing:
            - total_count: The total count of subject PDFs in the study.
            - Forms: Multiple forms for adding, removing, notifying, and deleting subjects.
            - user email: The email of the user retrieved from the session data.
    """
    context = {}

    user_details = SessionManager.get_specific_session_data(session_key,
                                                            constants.session_key_user_details, [])
    context["total_count"] = count_number_of_subject_pdf(study_name)
    context[constants.key_name_new_subjects_form] = CreateSubjectForm()

    context[constants.key_name_remove_subjects_form] = RemoveSubjectsForm(
        receivers=context[constants.key_name_subject_details]
                        [constants.key_name_ids_to_be_removed])

    context[constants.key_name_notification_form] = SendNotificationForm(
        receivers=context[constants.key_name_subject_details]
                    [constants.key_name_ids_to_be_removed])

    context[constants.key_name_delete_subject_form] = DeleteSubjectForm()
    context[constants.field_name_email] = user_details[constants.field_name_email]
    return context

def context_for_question_page(survey_id,question_id):
    context = {}
    question_details = {}   
    survey_details = retrieve_survey_details(survey_id)
    questions = retrieve_all_questions_for_survey(survey_id)
    context[constants.key_name_question_id] = question_id
    context[constants.key_name_survey_title] = survey_details["title"]
    context[constants.key_name_survey_id] = survey_id 
    category_details = retrieve_all_categories_for_survey(survey_id)
    context[constants.key_name_question_help_text] = get_help_texts_for_question_form()
    
    if question_id == 0:
        context[constants.key_name_question_form] = QuestionForm(initial={'sortId': len(questions) + 1}, categories=category_details)
        AnswerFormSet = formset_factory(AnswerForm, extra=1)
        question_details[constants.key_name_answer_formset] = AnswerFormSet()
    else:    
        question_details = retrieve_question_details(question_id)
        #change the clockTimes to string
        question_details = modify_questions_list_to_string(question_details)
        AnswerFormSet = formset_factory(AnswerForm, extra=0)
        question_details[constants.key_name_answer_formset] = AnswerFormSet(initial=question_details["answer"])       
        context[constants.key_name_question_form] = QuestionForm(data=question_details, categories=category_details)
        paired = zip(question_details[constants.key_name_answer_formset], question_details["answer"])
        context["paired"] = paired
    context[constants.key_name_question_details] = question_details   
    return context
   
def context_for_create_survey_page(survey_id):
    """
    Generate the context for rendering the create survey page.

    Args:
        survey_id (int): The ID of the survey for which the context is being created.

    Returns:
        dict: A dictionary containing:
            - survey_form: Form pre-filled with survey details.
            - question_form: Form for creating a new question.
            - answer_form: Form for creating new answers.
            - survey metadata: Includes survey ID, title, questions, and categories.
            - category_formset: A formset for creating and managing survey categories.
            - help_texts: Help texts for category and question forms.
    """
    logger.info("context_for_create_survey_page %s",survey_id)
    context = {constants.key_name_collect_flag : False}
    extra = 1
    if(survey_id != 0):
        survey_details = retrieve_survey_details(survey_id)
        category_details = retrieve_all_categories_for_survey(survey_id)
        question_details_list = retrieve_all_questions_for_survey(survey_id)
        for question_details in question_details_list:
            question_details = modify_questions_list_to_string(question_details)
        context[constants.key_name_survey_form] = SurveyForm(data=survey_details)
        context[constants.key_name_question_form] = QuestionForm(categories=category_details)
        AnswerFormSet = formset_factory(AnswerForm, extra=1)
        for question in question_details_list:
            question[constants.key_name_answer_formset] = AnswerFormSet(initial=question["answer"])

        context[constants.key_name_survey_id] = survey_id # can send all below in one json
        context[constants.key_name_survey_title] = survey_details["title"]
        context[constants.key_name_questions] = question_details_list # retrieve all questions relating to the survey id
        context[constants.key_name_categories] = category_details
        if len(category_details) > 0:
            extra = 0
            context[constants.key_name_collect_flag] = category_details[0]['didSubjectAsk']
        CategoryFormSet = formset_factory(CategoryForm, extra=extra)
        context[constants.key_name_category_formset] = CategoryFormSet(initial=category_details)# retrieve categories list of the survey
        context[constants.key_name_category_help_text] = get_help_texts_for_category_form()
        context[constants.key_name_survey_help_text] = get_help_texts_for_survey_form()
    return context


def context_for_survey_list_page():
    """
    Generate the context for rendering the survey list page.

    Returns:
        dict: A dictionary containing:
            - survey_jsonform: Form for uploading survey data in JSON format.
            - survey_form: Form for creating a new survey.
            - question_form: Form for creating a new question.
            - survey_help_text: Help text for the survey form.
    """
    context = {}
    context[constants.key_name_survey_jsonform] = JSONUploadForm()
    context[constants.key_name_survey_form] = SurveyForm()
    context[constants.key_name_question_form] = QuestionForm()
    context[constants.key_name_survey_help_text] = get_help_texts_for_survey_form()
    return context
