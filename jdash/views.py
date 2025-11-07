###########################################################################
####               Views.py
####           Interface file to map each function to its service/methods
####           created by mnarava
####
####
###########################################################################

from django.http.response import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.forms.formsets import formset_factory
from django.core.cache import cache
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages, auth
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.db import IntegrityError
import logging, json
from datetime import datetime
import logging, json
from datetime import datetime
from jdash.classes.controller import download_dataset,initiate_download_study_dataset, dowload_unused_qr_code_files, download_subject_qr_file
from jdash.classes.controller import create_new_study,update_survey_details,delete_question_from_survey,delete_question_from_file,download_ics_file
from jdash.classes.controller import duplicate_and_create_new_question_id
from jdash.models import FileDownloadToken
from jdash.classes.datahelper import get_contactus_form_data, get_question_form_data 
from jdash.classes.survey import generate_survey_json_for_download
from jdash.classes.datahelper import   get_survey_form_data,get_notification_form_data, get_info_texts
from jdash.classes.controller import duplicate_and_create_new_survey_id,context_for_survey_list_page,upload_survey_json_file
from jdash.classes.controller import update_study_meta_data,create_display_sop_list_of_study,update_categories_for_survey
from jdash.classes.controller import delete_subjects_from_server,remove_subjects_from_study,get_all_survey_details
from jdash.classes.controller import update_survey_details,create_question_answer_for_survey,update_question_answer_for_survey
from jdash.classes.controller import context_for_create_survey_page,create_survey_from_surveyForm,update_survey_from_surveyForm,context_for_question_page
from jdash.forms import CreateStudyForm, SurveyForm, DeleteSubjectForm, SendNotificationForm, ContactUsForm
from jdash.forms import JSONUploadForm, RemoveSubjectsForm, CreateSubjectForm, TaskForm, QuestionForm
from jdash.forms import CategoryForm,AnswerForm
from jdash.classes.study import get_all_study_details, display_study, close_study
from jdash.classes.fileutils import get_json_data,get_study_name_from_subject_id
from jdash.classes.fileutils import to_list
from jdash.classes.study import update_number_of_subjects
from jdash.classes.subject import create_subjects_for_study, count_number_of_subject_pdf
from jdash.classes.notification import send_push_notification, send_email
from jdash.apps import constants as constants
from jdash.classes.dbutils import delete_survey_for_user,get_group_name_for_user,retireve_all_studies_for_user
from jdash.classes.dbutils import  update_test_case_flags
from jdash.classes.dbutils import retrieve_all_survey_for_user,set_email_for_user
from jdash.interface.session_manager import SessionManager
from jdash.textmessages import TextMessages as textmessages
logger = logging.getLogger("django")


@login_required
def index(request):
    """
    This view function checks if a user is authenticated. If so, it retrieves or fetches 
    study metadata and statistics, updates session data accordingly, and renders the 
    appropriate template (home or error page). If the user is not authenticated, it 
    redirects to the login page.

    Args:
        request (HttpRequest): The HTTP request object.

    Returns:
        HttpResponse: Renders the home page if authenticated and data is successfully 
        retrieved or cached. If an error occurs, the error page is rendered. If the 
        user is not authenticated, the login page is rendered.
    """
    context = {}
    if request.user.is_authenticated:
        logged_user = request.user
        study_meta = {}
        stats = {}
        error_message = ""
        try:
            logger.info("userdetail retrieving",SessionManager.get_specific_session_data(request.session.session_key,constants.session_key_user_details,[]))
            study_meta =  SessionManager.get_specific_session_data(request.session.session_key,constants.session_key_studies,None)
            stats =  SessionManager.get_specific_session_data(request.session.session_key,constants.session_key_studies_stats,None)
            
            if not study_meta:
                logger.info("storing values in session")
                study_meta, stats, error_message= get_all_study_details(logged_user)
                list_of_studies = {}
                list_of_studies = {study['title']: study['title'] for study in study_meta}

                cache.set(constants.session_key_list_studies,list_of_studies,timeout=3600)

                if not error_message:
                    session_studies_ema = request.session.get(constants.session_key_studies_ema, [])
                    session_old_studies_ema = request.session.get(constants.session_key_old_ema, [])
                    for study in study_meta:
                        if constants.ema in study[constants.key_name_sensor_list]:
                            session_studies_ema.append(study[constants.key_name_study_title])
                        if "old_ema" in study:
                            session_old_studies_ema.append(study[constants.key_name_study_title])
                    # store the survey_details from the databases.
                    logger.info("ema studies %s",list(set(session_studies_ema)))
                    logger.info("old ema studies %s",list(set(session_old_studies_ema)))
                    # Update session only once to minimize writes
                    request.session[ constants.session_key_studies]=study_meta  
                    request.session[ constants.session_key_studies_stats]= stats  
                    request.session[constants.session_key_studies_ema]= list(set(session_studies_ema))
                    request.session[constants.session_key_old_ema]= session_old_studies_ema
                    request.session.modified = True 
                else:
                    return render(request, constants.error_page, context)
            else:
                logger.info("accessing values from session")
            context[constants.key_name_study_meta] = study_meta
            context[constants.key_name_stats] = stats
            context[constants.key_name_error_message] = error_message
            return render(request, constants.home_page, context)
        
        except Exception as e:
            logger.info("Loading Home Page error %s ",e)
            return render(request, constants.error_page, context)
    else:
        return render(request, constants.login_page)


def login_request(request):
    """
    This view processes a POST request containing user credentials via Django's 
    `AuthenticationForm`. If the credentials are valid, the user is authenticated, 
    logged in, and relevant user and group information is stored in the session. 
    If the login fails, appropriate error messages are displayed. 

    Args:
        request (HttpRequest): The HTTP request object containing user input data.

    Returns:
        HttpResponse: Redirects to the home page upon successful login, 
        or re-renders the login page with appropriate forms and error messages.
    """
    context = {}
    if request.method == constants.post_method:
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get(constants.field_name_username)
            password = form.cleaned_data.get(constants.field_name_password)
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # Storing additional user details in session
                request.session[constants.session_key_user_details]= {
                                    constants.session_key_username : user.username,
                                    'email': user.email,
                                    'first_name': user.first_name,
                                    'last_name': user.last_name,
                                }

                request.session[constants.session_key_groupname] = get_group_name_for_user(user)
                request.session.modified = True
                #messages.info(request, f"You are now logged in as  .")
                return redirect(constants.url_name_for_home)
            messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    context[constants.key_name_login_form] = AuthenticationForm()
    context[constants.key_name_contact_form] = ContactUsForm()
    return render(request=request, template_name=constants.login_page, context=context)


def csrf_failure(request, reason=""):
    """
    Method for to handle form expiry redirection
    """
    messages.error(request, "Session expired. Please log in again.")
    return redirect('/login/')

@login_required
def logout_request(request):
    """
    Method for logout

    :param request:
    :return:
    """
    logout(request)
    auth.logout(request)
    return redirect(constants.url_name_for_login)

##########      Endpoints methods related to study creation, editing, and deletion          ########

@login_required
def study_details(request, study_name):
    """
    Handles various study-related actions based on user input (POST requests).

    Processes form submissions for sending notifications, creating/removing subjects, 
    and deleting subject data for a specific study. Updates the study context with 
    relevant forms, subject counts, and error messages.

    Args:
        request (HttpRequest): The HTTP request object containing the form data.
        study_name (str): The name of the study being updated.

    Returns:
        HttpResponse: The rendered page with updated context, including forms and error messages.
    """
    context = display_study(study_name)
    user_details = SessionManager.get_specific_session_data(request.session.session_key, 
                                                            constants.session_key_user_details, [])

    if constants.button_name_send_notification in request.POST:
        form = SendNotificationForm(request.POST, 
                                    receivers=context[constants.key_name_subject_details]
                                    [constants.key_name_ids_to_be_removed])
        if form.is_valid():
            message_title,message_text,receivers = get_notification_form_data(form)
            send_push_notification(message_title,message_text,receivers,study_name )
    elif constants.button_name_create_subjects in request.POST:
        form = CreateSubjectForm(request.POST)
        if form.is_valid():
            total_count = create_subjects_for_study(study_name,
                                                    form.cleaned_data.get(constants.field_name_number_of_subjects))
            # update the number to study.json
            update_number_of_subjects(study_name, total_count)
            
    elif constants.button_name_remove_subjects in request.POST:
        form = RemoveSubjectsForm(request.POST,
                                receivers=context[constants.key_name_subject_details]
                                [constants.key_name_ids_to_be_removed])
        if form.is_valid():
            context = remove_subjects_from_study(study_name,
                                                form.cleaned_data.get(constants.field_name_subject_to_remove),
                                                context)
    elif constants.button_name_delete_subject_data in request.POST:
        # we need all the study ids from the modal form coma sepreated
        selected_ids = request.POST[constants.field_name_subjectId]
        delete_subjects_from_server(study_name,selected_ids)



    if constants.key_name_error_message in context:
        study_meta, stats,error_message = get_all_study_details(request.user)
        context.update({
            constants.key_name_study_meta: study_meta,
            constants.key_name_stats: stats,
            constants.key_name_error_message: error_message
        })
        return render(request, constants.home_page, context)
    context["total_count"] = count_number_of_subject_pdf(study_name)
    subject_ids_to_remove = [] # empty list if error due to subjects parsing during display_study
    if constants.key_name_subject_details in context:
        # Prepare subject details
        subject_details = context[constants.key_name_subject_details]
        subject_ids_to_remove = subject_details[constants.key_name_ids_to_be_removed]
    context.update({
        constants.key_name_new_subjects_form: CreateSubjectForm(),
        constants.key_name_remove_subjects_form: RemoveSubjectsForm(receivers=subject_ids_to_remove),
        constants.key_name_notification_form: SendNotificationForm(receivers=subject_ids_to_remove),
        constants.key_name_delete_subject_form: DeleteSubjectForm(),
        constants.field_name_email: user_details[constants.field_name_email]
    })
    return render(request, constants.details_page, context)


@login_required
def close(request, study_name):
    """
    Method for close Studies

    :param request:
    :param study_name:
    :return:
    """
    context = {}
    context[constants.key_name_study_meta], context[constants.key_name_stats],context[constants.key_name_error_message] = close_study(study_name, request.user)
    if not context[constants.key_name_error_message]:
        return render(request, constants.home_page, context=context)

    return render(request, constants.error_page, context=context)


@login_required
def download_unused_files(request, arg):
    """
    Downloads files based on the provided argument.

    :param request: The HTTP request object.
    :param arg: The argument that determines which files to download (subject_id, study_data, or qrfiles).
    :return: A response with the appropriate download or error page.
    """
    try:
        if "00" in arg:
            return download_subject_qr_file(arg)

        elif "data" in arg:
            data = request.POST
            logger.info("details from the request %s",data)
            # get the email from the request post
            user_details = request.session.get('user_details', {})
            if user_details[constants.field_name_email] == '':
                user_details[constants.field_name_email] = data["user_email"]
                request.session[constants.session_key_user_details]= user_details
                request.session.modified = True
                #update user details in db and session
                set_email_for_user(user_details[constants.field_name_username],data["user_email"])
            initiate_download_study_dataset(data[constants.key_name_study_name],
                                            data[constants.key_name_type],user_details)
            return study_details(request,data[constants.key_name_study_name])
        
        return dowload_unused_qr_code_files(arg)
    except Exception as e:
        logger.info("Unexpected Error %s ",e)
        return render(request, constants.error_page, context={})

def download_dataset_from_link(request, arg):
    """
    Handles the download of study data using a token sent via email.

    This method checks the validity of the token (based on its expiration date) 
    and verifies the provided confirmation code. If the token is valid, the 
    corresponding study data is downloaded. If the token is invalid or expired, 
    an error page is displayed. If the email address is not provided, the user 
    is prompted to input it.

    :param request: The HTTP request object, which contains the GET parameters and session data.
    :param arg: The token used to identify and validate the download request.
    :return: A response to either download the dataset or render an error or confirmation page.
    """
    #check the table for file and token and 1 week date
    if constants.button_name_download_data_confirm in request.GET:
        logger.info("Ready to download")
        try:
            download_token = FileDownloadToken.objects.get(token=arg,
                                                        expiration_date__gte=datetime.now().astimezone())
            if download_token.code != request.GET['verifyCode'] :
                messages.error(request, "Invalid code. ")
                return render(request, constants.download_confirm, context={'arg' :arg})
        except FileDownloadToken.DoesNotExist:
            return render(request, constants.error_page, context={})
        study_name = download_token.file_name
        logger.info("download request for %s data",study_name)
        #update the csv for downloaded timestamp
        return download_dataset(study_name)
    # if email not present present a input for email address and store in the filedownloadToken
    #get email address from the database
    db_object = FileDownloadToken.objects.get(token=arg,
                                            expiration_date__gte=datetime.now().astimezone())
    send_email("",db_object.email,arg,"confirm")
    return render(request, constants.download_confirm, context={'arg' :arg})


@login_required
def add_study(request):
    """
    Method for add new Studies

    :param request:
    :return: context json with study meta
    """
    context = {}
    error = ""
    success = ""
    # To pop up all surveys user created in the add form 
    survey_list_obj = retrieve_all_survey_for_user(request.user,request.session.session_key) 
    TaskFormSet = formset_factory(TaskForm)

    if request.method == constants.post_method:
        form = CreateStudyForm(request.POST, request.FILES,survey = survey_list_obj)
        formset = TaskFormSet(request.POST)
        if form.is_valid():
            context = create_new_study(form,formset,request)
            request.session[constants.session_key_studies]= None
            if not context[constants.key_name_error_message]:
                logging.info("adding new study successfully:end ")
                # To return page to home page with list of all studies including new study 
                return render(request, constants.home_page, context=context)

    context[constants.key_name_study_name] = ""
    form = CreateStudyForm(survey= survey_list_obj)
    task_formset = TaskFormSet()
    context[constants.key_name_study_meta], context[constants.key_name_stats],error = get_all_study_details(request.user)
    context[constants.key_name_study_form] = form
    context[constants.key_name_task_formset] = task_formset
    context[constants.key_name_info_text] = get_info_texts()   
    messages.success(request,  success)
    if not error:
        # To return page to create study with al forms 
        return render(request, constants.create_study_page, context)
    messages.error(request, error)
    context[constants.key_name_error_message] = error
    return render(request, constants.error_page, context)


@login_required
def edit_study(request, study_name):
    """
    Method for edit Studies

    :param request:
    :return:
    """
    context = {}
    error = ""
    survey_list_obj = retrieve_all_survey_for_user(request.user,request.session.session_key)
    json_meta = get_json_data(study_name)
    if request.method == constants.post_method:
        TaskFormSet = formset_factory(TaskForm)
        formset = TaskFormSet(request.POST)
        form = CreateStudyForm(request.POST,survey= survey_list_obj)

        if constants.button_name_update_study in request.POST:
            if form.is_valid():
                context = update_study_meta_data(study_name,form, formset, request)
                context[constants.key_name_survey_form] = SurveyForm()
                context[constants.key_name_question_form] = QuestionForm()
                messages.success(request, textmessages.success_study_updated)
                request.session[constants.session_key_survey_details]= None
                return render(request, constants.home_page, context=context)

    if "survey" in json_meta:
        if "id" not in json_meta["survey"]:
            context["is_file"] = True
            context[constants.key_name_study_form] = CreateStudyForm(data=json_meta,survey = survey_list_obj)
        else:
            logger.debug("json in the attached study file %s",json_meta)
            context["is_file"] = False
            context[constants.key_name_study_form] = CreateStudyForm(data=json_meta,survey = survey_list_obj,initial_survey_id = json_meta["survey"]["id"])
    else:
        context[constants.key_name_study_form] = CreateStudyForm(data=json_meta,survey = survey_list_obj)
    if constants.key_name_task_list in json_meta:
        TaskFormSet = formset_factory(TaskForm, extra=1)
        context[constants.key_name_task_formset] = TaskFormSet(initial=json_meta[constants.key_name_task_list])
    else:
        TaskFormSet = formset_factory(TaskForm, extra=1)
        context[constants.key_name_task_formset] = TaskFormSet()
    context[constants.key_name_study_name] = study_name
    context[constants.key_name_number_of_subjects] = json_meta[constants.key_name_number_of_subjects]
    context[constants.key_name_is_survey] = True if constants.key_name_survey in json_meta else False

    messages.error(request, error)
    return render(request, constants.edit_study_page, context=context)

@login_required
def qc_study(request,study_name):
    """
    Method for displaying sop list
    For new study if no sops, create and send the list
    :param request: study_name
    :return: sop_dict
    """
    if "update_test_flags" in request.POST:
        test_flags_list = request.POST['test_case_flags']
        user_details = request.session.get('user_details', {})
        update_test_case_flags(json.loads(test_flags_list),user_details[constants.field_name_username])
    context = create_display_sop_list_of_study(study_name)
    return render(request, constants.sop_list_of_study_page, context)


def download_calendar_for_subject(request,study_name,subject_id):
    """
    Handles the download of a calendar for a specific subject.

    Endpoint: /download/ics/<subject_id>

    Args:
        request (HttpRequest): The HTTP request object containing metadata about the request.
        arg (str): The subject ID for which the calendar is to be downloaded.

    Returns:
        HttpResponse: A response object that contains the calendar file for the specified subject.
    """

    try:
        return download_ics_file(study_name,subject_id)
    except Exception as e:
        logger.info("download_calendar_for_subject::Unexpected Error %s ",e)
        return render(request, constants.error_page, context={})

##########      Endpoints methods related to survey creation, editing, and deletion          ########
@login_required
def create_survey(request, survey_id=0,question_id=0):
    """
    Handles survey creation, update, question management, and JSON upload actions.

    This view supports multiple POST operations based on the button pressed in the request:
    - Uploading a survey via a JSON file.
    - Creating a new survey from a form.
    - Updating survey metadata.
    - Adding, deleting, or updating questions and their answers.

    On successful operations, it either updates the session to invalidate cached survey data
    or returns the updated context for rendering the create survey page. If an error occurs,
    appropriate messages are added to Django's messages framework.

    Args:
        request (HttpRequest): The HTTP request object with form data and user info.
        survey_id (int, optional): ID of the survey being modified. Defaults to 0.
        question_id (int, optional): ID of the question being modified. Defaults to 0.

    Returns:
        HttpResponse: Rendered response for the create or general survey page,
                      depending on success or failure of the operation.
        context: dictionary containing the survey details.
    """
    context= context_for_create_survey_page(survey_id)
    try:
        if constants.button_name_upload_survey in request.POST:
            form = JSONUploadForm(request.POST)
            if form.is_valid:
                survey_json_file = request.FILES["json_file"].read()
                context = upload_survey_json_file(survey_json_file,request.user)
        elif constants.button_name_create_survey in request.POST:
            tzname = request.headers.get('Timezone')
            logger.info("Timezone from header",tzname)
            form = SurveyForm(request.POST)
            logger.info(form.errors)
            if form.is_valid:
                form_data = get_survey_form_data(form)
                context = create_survey_from_surveyForm(form_data,request.user)
        elif constants.button_name_update_survey_info in request.POST:
            form = SurveyForm(request.POST)
            logger.debug(form.errors)
            if form.is_valid:
                form_data = get_survey_form_data(form)
                context = update_survey_from_surveyForm(form_data,survey_id)
           
        elif constants.button_name_delete_question in request.POST:
            survey_id = request.POST[constants.key_name_survey_id]
            question_id = request.POST[constants.field_name_question_id]
            context = delete_question_from_survey(question_id,survey_id)
        # making session variable None to update the session during retreiving the list again
        request.session[constants.session_key_survey_details]= None
    except TypeError as e:
        # Handle database integrity error, e.g., unique constraint violation
        logger.info("TypeError: %s", e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
    except IntegrityError as e:
        # Handle database integrity error, e.g., unique constraint violation
        logger.info("IntegrityError: %s", e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
    except Exception as e:
        # Catch other database-related errors
        logger.info("Unexpected Error: %s", e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
    
    return render(request, constants.create_survey_page, context=context)

@login_required
def manage_question(request, survey_id=0,question_id=0):
    """
    Method for Create/Edit Questions

    param: survey_id
    return: context json with all the forms, question list json
    """
    context= {}
    form = QuestionForm(request.POST)           
    AnswerFormSet = formset_factory(AnswerForm)
    answer_form = AnswerFormSet(request.POST)  
    logger.info(request.POST) 
    try:
        if constants.button_name_add_question in request.POST:
            logger.info(form.errors)
            if form.is_valid() :
                context = create_question_answer_for_survey(survey_id,form,answer_form)   
                return render(request, constants.create_survey_page, context=context)   
            
        elif constants.button_name_update_question in request.POST:            
            answer_id_list = request.POST.getlist('answer_id')
            logger.info(answer_id_list)
            logger.info(form.errors)
            if form.is_valid:
                context = update_question_answer_for_survey(question_id,form,answer_id_list,answer_form) 
                return render(request, constants.create_survey_page, context=context)
        
    except TypeError as e:
        # Handle database integrity error, e.g., unique constraint violation
        logger.info("TypeError: %s", e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
    except IntegrityError as e:
        # Handle database integrity error, e.g., unique constraint violation
        logger.info("IntegrityError: %s", e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
    except Exception as e:
        # Catch other database-related errors
        logger.info("Unexpected Error: %s", e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
    context=context_for_question_page(survey_id,question_id)
    if question_id == 0:
        return render(request, constants.create_question_page, context=context)
    return render(request, constants.edit_question_page, context=context)
    
    
      
@login_required
def download_survey_json(request,survey_id):
    """
    Method for downloading survey json file

    :param request:
    :param survey_id:
    :return:
    """
    logger.info("download_survey_json")
    data = json.dumps(generate_survey_json_for_download(survey_id),indent=4,ensure_ascii=False)

    # Set the return value of the HttpResponse
    response = HttpResponse(data, content_type='application/json')
    # Set the HTTP header for sending to browser
    response['Content-Disposition'] = 'attachment; filename="survey.json"'
    # Return the response value
    return response


@login_required
def manage_category_for_survey(request, survey_id=0):
    """
    Method for Create/Edit categories

    param: survey_id
    return: context json with all the forms, category list json 
    """
    context = {}
    try:
        collect_subject_id = request.POST.get(constants.key_name_collect_subject_id_flag, False)
        collect_flag = True if collect_subject_id == 'on' else False
        CategoryFormSet = formset_factory(CategoryForm)
        formset = CategoryFormSet(request.POST)        
        logger.info(formset.errors)
        if formset.is_valid() :
            context = update_categories_for_survey(survey_id,collect_flag,formset)
        context = context_for_create_survey_page(survey_id)
    except Exception as e:
        context = context_for_create_survey_page(survey_id)
        logger.error("Unexpected Error %s ",e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
    return render(request, constants.create_survey_page, context)

@login_required
def duplicate_survey(request, survey_id=0):
    """
    Method for duplicate survey from exisitng one

    :param request: survey_id
    :return: updated survey_list
    """
    context = {}
    context = duplicate_and_create_new_survey_id(survey_id,request.user,request.session.session_key)
    return render(request, constants.survey_page, context)


@login_required
def duplicate_question(request, survey_id=0,question_id=0):
    """
    Method for duplicate survey from exisitng one

    :param request: survey_id
    :return: updated survey_list
    """
    context = {}
    context = duplicate_and_create_new_question_id(survey_id,question_id)

    return render(request, constants.create_survey_page, context=context)

@login_required
def delete_survey(request):
    """
    Method for delete survey

    :param request:
    :return:
    """
    context = {}
    try:
        if constants.button_name_delete_survey in request.POST:
            groupname = SessionManager.get_specific_session_data(request.session.session_key,
                                                                constants.session_key_groupname,None)

            result = delete_survey_for_user(groupname,request.user,request.POST['survey_id'])
            # remove the entry from the session 
            #SessionManager.delete_specific_session_valuedata(request.session.session_key, constants.session_key_survey_details,"id",obj['survey_id'])
            #request.session.modified = True
            request.session[constants.session_key_survey_details]= None
            if result:
                return render(request, constants.survey_page, context=get_all_survey_details(request.user,request.session.session_key))
    except Exception as e:
        logger.error("Unexpected Error %s ",e)
        messages.error(request, f"{e} : Please write to support email for assistance.")
        return render(request, constants.survey_page, context=get_all_survey_details(request.user,request.session.session_key))
    
@login_required
def edit_survey(request, study_name):
    """
    Method can be dissolved once the old surveys are migrated to database
    Editing survey details and for old studie with id =999

    Error messages (if any) from the data retrieval process are shown to the user.

    Args:
        request (HttpRequest): The HTTP request object
        study_name (str): The name of the study json to be updated. 

    Returns:
        context: dictionary containing the necessary forms.
    """
    context = {}
    context[constants.key_name_study_name] = study_name
    study_json = get_json_data(study_name)
    if constants.button_name_update_question in request.POST:
        values_to_be_updated = {}
        form = QuestionForm(request.POST)
        answerForm = AnswerForm(request.POST)
        # save the updated values to json
        if form.is_valid():
            values_to_be_updated = get_question_form_data(form)
            values_to_be_updated[constants.key_name_id] = request.POST[constants.field_name_id_value]
            update_survey_details(study_name, values_to_be_updated)

    if constants.button_name_remove_question in request.POST:
        study_json = delete_question_from_file(study_name,request.POST[constants.key_name_question_title])

    if constants.key_name_error_message in context: 
        return render(request, constants.error_page, context)
        #context[constants.key_name_error_message] = "Unexpected Error: Please write to support email for assistance."

    context[constants.key_name_json_meta] = study_json
    context[constants.key_name_survey_form] =SurveyForm(request.POST)
    context[constants.key_name_question_form] = QuestionForm()
    context[constants.key_name_answer_form] = AnswerForm()
    return render(request, constants.edit_survey_page, context)

@login_required
def survey_list(request):
    """
    Renders the survey list page with session-based caching.

    This function attempts to retrieve the survey list from the user's session data
    to improve performance and reduce redundant database calls. If no survey list 
    is found in the session or if it's `None`, it fetches all survey details for 
    the user and updates the session accordingly.

    Error messages (if any) from the data retrieval process are shown to the user.

    Args:
        request (HttpRequest): The HTTP request object 

    Returns:
        context: dictionary containing the survey list with all details.
    """
    context = context_for_survey_list_page()
    context["survey_list"] = SessionManager.get_specific_session_data(request.session.session_key,
                                                                    constants.session_key_survey_details, [])
    if context["survey_list"] is None:
        context = get_all_survey_details(request.user,request.session.session_key)       
        if constants.key_name_error_message in context :
            context["survey_list"] = []
            messages.error(request, context[constants.key_name_error_message])
        request.session[constants.session_key_survey_details]=list(context["survey_list"])
        request.session.modified = True
    return render(request, constants.survey_page, context)

@login_required
def analytics(request, study_name):
    """
    Handles the analytics view for the given study.
    This function retrieves all studies associated with the logged-in user,
    processes the study data, and prepares the initail args for rendering the 
    analytics details page.
    
    Endpoint: /analytics/<study_name>
    
    Args:
        request (HttpRequest): The HTTP request object containing metadata 
            about the request, including the user and session information.
        study_name (str): The name of the study to display analytics for. 
            If "all", analytics for all studies will be displayed.
            
    Returns:
        HttpResponse: The rendered HTML response for the analytics details page.
        
    Notes:
        - The function assumes `retrieve_all_studies_for_user` is a utility 
          function that fetches all studies for the given user.
    """
    
    context = {}
    sensors_map = {}
    study_list = []
    study_dict = retireve_all_studies_for_user(request.user)
    # Extract study titles
    for study in json.loads(study_dict):
        study_list.append(study[constants.key_name_study_title])
        sensor_list = to_list(study[constants.key_name_sensor_list])
        sensors_map[study[constants.key_name_study_title]] = sensor_list
    if study_name == "all":
        context[constants.key_name_study_name] = "all"
    else:
        #json_meta = get_json_data(study_name)
        context[constants.key_name_study_name] = study_name.lower()
    context[constants.key_name_session_id]= request.session.session_key
    context = {
        'initial_args': {
            "study-store": {
                "data": study_list
            },
            "sensor-store": {
                # map: study -> list of sensors
                "data": sensors_map
            }
        }
    }
    logger.debug("analytics:: study name %s",context)
    # Render the HTML template index.html with the data in the context variable.
    return render(request, constants.analytics_details_page, context=context)

##########      Endpoints Methods for no login requests    ###############

def delete_subject_data(request):
    """
    Method for deleting subject data
    
    :param request:
    :return:
    """
    logger.info("delete_subject_data:::")
    context= {}
    study_list = []
    if constants.url_name_for_delete_subject_data in request.POST:
        form = DeleteSubjectForm(request.POST)
        if form.is_valid():
            selected_id = form.cleaned_data.get(constants.field_name_subjectId)
            email = form.cleaned_data.get(constants.field_name_email)
            reason = form.cleaned_data.get(constants.field_name_reason)
            # sending email to support email specifying the request of delete request of subject ids
            send_email(selected_id,email,"","delete_subject")
            #delete_subjects_from_server(selected_ids)
            context['text_message'] = textmessages.success_deletion_data_request
            return render(request, constants.success,context)
    context[constants.key_name_delete_subject_form] = DeleteSubjectForm()
    return render(request, constants.delete_subject,context)


def contact_email(request):
    """
    Method for deleting subject data
    
    :param request:
    :return:
    """
    logger.info("contact_email:::")
    context= {}
    if constants.button_name_contact_message in request.POST:
        form = ContactUsForm(request.POST)
        logger.info(form.errors)
        if form.is_valid():
            fullname, sender_email, message = get_contactus_form_data(form)
            send_email(fullname, sender_email, message,"")
            context['text_message'] = textmessages.success_contacting_message
            return render(request, constants.success,context)
    context[constants.key_name_contact_form] = ContactUsForm()
    return render(request, constants.contact_us,context)


def studies_list(request):
    """
    Method for studies_list for dash app
    
    :param request:
    :return:
    """
    logger.info("studies_list:::%s",request.session.session_key)
    study_list = []
    study_dict = retireve_all_studies_for_user(request.user)
    # Extract study titles
    for study in json.loads(study_dict):
        study_list.append(study[constants.key_name_study_title])
    
    # Return study list as JSON
    return JsonResponse({"studies": study_list}, status=200)




