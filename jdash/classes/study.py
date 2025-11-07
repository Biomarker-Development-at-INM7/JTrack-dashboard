###########################################################################
####           study.py
####           this file contains all the service methods related to studies
####           initial version written by mstolz
####           reproduced/modified by mnarava
####
####
###########################################################################

import base64
import json
import logging
import os
from datetime import datetime
import numpy as np
import pandas as pd
from jdash.classes.fileutils import get_json_data
from pandas.errors import EmptyDataError
import jdash.exceptions.studyexceptions as studyexceptions
from jdash.apps import constants as constants
from jdash.apps import jdashConfig as config
from jdash.classes.datahelper import validate_empty
from jdash.classes.subject import Subject
from jdash.classes.subject import get_subject_details, create_subjects_for_study
from jdash.classes.dbutils import create_new_study_in_db, retireve_all_studies_for_user, close_study_model
from jdash.classes.dbutils import retrieve_survey,create_survey_in_db
from jdash.classes.fileutils import read_study_df, get_user_list, get_ids_and_app_list, get_all_json_data
from jdash.classes.fileutils import parse_get_dashboard_csv,create_backup_json_file
from jdash.classes.fileutils import change_permissions,save_study_json,open_study_json
from jdash.classes.survey import generate_survey_json_for_download

logger = logging.getLogger("django")
response = False
errors = ""
# Get the current date in the desired format
current_date = datetime.strftime(datetime.now().astimezone(),'%Y-%m-%d')


class Study:
    """Class representing a Study"""
    def __init__(self, json_meta):
        self.study_name = json_meta.get("name", "")
        self.study_description = json_meta.get("description", "")
        self.enrolled_subjects = json_meta.get("enrolled_subjects", [])
        self.number_of_subjects = json_meta.get("number-of-subjects", json_meta.get("number_of_subjects", 0))
        self.study_duration = json_meta.get("duration", "")
        self.sensors = [sensor_column.split(' ')[0] for sensor_column in json_meta.get("sensor_list", []) if 'n_batches' in sensor_column]
        self.frequency = json_meta.get("frequency", "")
        self.labelling = json_meta.get("active_labeling", "")
        self.ids_with_missing_data = []


def create_study(study_dict, user):
    """
    Create study using underlying json data which contains study_name, initial number of subjects, study duration and a list
    of sensors to be used. The new study is created in the storage folder. Further,
    folders for qr codes and subjects sheets will be create within the dashboard project and filled with corresponding qr codes
    and pdfs. Lastly, a json file containing meta data of the study is stored.

    response = True or False depending if creation succeeded. False if and only if study already exists.
    
    :param study_dict: 
    :param user: 
    :return: 
    """
    images_url = ""
    errors = ""
    survey = None
    try:
        study_path = os.path.join(config.studies_folder, study_dict[constants.field_name_name])
        if os.path.isdir(study_path):
            raise studyexceptions.StudyAlreadyExistsException
        os.mkdir(study_path)
        change_permissions(study_path)
        # make <study>/outputs folder in studies_bids directory for analysis
        studies_bids_path = os.path.join(config.analytics_storage_folder, study_dict[constants.field_name_name])
        if not os.path.isdir(studies_bids_path):
            os.mkdir(studies_bids_path)
            change_permissions(studies_bids_path)
            os.makedirs(os.path.join(studies_bids_path, config.analytics_outputs_folder), exist_ok=True)
        
        os.makedirs(os.path.join(config.dash_folder, config.app_study_folder, study_dict[constants.field_name_name], config.qr_folder),
                    exist_ok=True)

        change_permissions(os.path.join(config.dash_folder, config.app_study_folder, study_dict[constants.field_name_name]))

        os.makedirs(os.path.join(config.dash_folder, config.app_study_folder, study_dict[constants.field_name_name], config.sheets_folder),
                    exist_ok=True)

        if constants.field_name_images in study_dict:
            if study_dict[constants.field_name_images] in study_dict:
                ema_images_bytes = base64.b64decode(study_dict[constants.field_name_images])
                with open(os.path.join(study_path, study_dict[constants.field_name_name] + '_images.zip'), 'wb') as zf:
                    zf.write(ema_images_bytes)
                    study_dict[constants.field_name_images] = True
                    images_url = constants.images_folder
        else:
            study_dict[constants.field_name_images] = False
 
        if constants.field_name_survey in study_dict:
            if isinstance(study_dict[constants.field_name_survey], int):
                survey = retrieve_survey(study_dict[constants.field_name_survey])
            else:
                survey = create_survey_in_db(study_dict[constants.field_name_name],study_dict[constants.field_name_survey],user) if constants.field_name_survey in study_dict else None

            if survey is not None:
                study_dict[constants.field_name_survey] = generate_survey_json_for_download(survey.id)
        study_dict["version"] = 1
        # store json file with data
        save_study_json(study_dict[constants.field_name_name], study_dict)
        logger.info(study_dict,survey)
        # make new study and studygroup
        create_new_study_in_db(user, study_dict,survey,images_url)
        # create subjects depending on initial subject number
        create_subjects_for_study(study_dict[constants.field_name_name], study_dict['number-of-subjects'])
        
        response = True
    except studyexceptions.StudyAlreadyExistsException as se:
        logger.info(se.message)
        errors = se.message
        response = False
    except ValueError as ve:
        logger.info(ve)
        errors = ve
        response = False
    except Exception as e:
        logger.info("Unknown Exception Occurred %s",e)
        errors = "Unknown Exception Occurred"
        response = False

    return response, errors

def get_all_study_details(user):
    """
    Method for retrieving all study details
    Requests to database and forms the total_study_dict, stats_json
    """
    stats_json = {}
    total_study_dict = []
    error_message = ""
    try:
        study_dict = retireve_all_studies_for_user(user)
        for study in json.loads(study_dict):
            study[constants.key_name_created_date] = study[constants.key_name_created_date]
            json_data = get_json_data(study[constants.key_name_study_title])
            if constants.key_name_sensor_list in json_data:
                study[constants.key_name_sensor_list] = json_data[constants.key_name_sensor_list]
                res = study[constants.key_name_sensor_list]
                if constants.key_name_survey in json_data:
                    res.append(constants.ema)
                if isinstance(res, str):
                    res = [res]
                if constants.field_name_labeling in json_data:
                    if json_data[constants.field_name_labeling] is not None and json_data[constants.field_name_labeling] > 0 :
                        res.append(constants.field_name_labeling)
                study[constants.key_name_sensor_list] = res  
                # study[constants.key_name_sensor_list] = study[constants.key_name_sensor_list].append(constants.ema)
            study[constants.key_name_current_sensor_list] = get_latest_received_study_sensor_details(study[constants.key_name_study_title])
            stats_json = calculate_stats_of_number_of_subjects(study[constants.key_name_study_title],
                                                            json_data['number_of_subjects'])
            # to add old surveys with no ids in session and use for survey files listing
            if constants.key_name_survey in json_data:
                if "id" not in json_data[constants.key_name_survey]:
                    study["old_ema"]= True
            study['stats'] = stats_json
            total_study_dict.append(study)
    except EmptyDataError as ed:
        logger.info("Empty Data Error %s",ed)
        error_message = "Empty Data Error"
    except Exception as e:
        logger.info("get_all_study_details::: Exception occurred %s",e)
        error_message = "Exception occurred"
    return total_study_dict, stats_json,error_message


def display_study(study_name):
    """
    display details of the a study

    :param study_name:
    :return:
    """
    context = {}
    ids_to_remove = {}
    logger.info("display_study::start::for:%s",study_name)
    try:
        # parse json from the study meta data
        context['meta_data'] = get_json_data(study_name)
        #study_object = Study(json_meta)
        logger.debug("display_study::succesfully created study object")
        data = parse_get_dashboard_csv(study_name)

        if "sensor_list" in context['meta_data']:
            # add other sensor keys to the data dictionary to avoid key error
            for sensor in context['meta_data']["sensor_list"]:
                for obj in data:
                    if sensor + ' n_batches' not in obj:
                        obj[sensor + ' n_batches'] = 0
                        obj[sensor + ' last_time_received'] = "none"
        # sorted and modified json to show in the template
        sorted_json, count = get_modified_json_form_csv(data)
        context['meta_data']['number_of_enrolled_subjects'] = count
        ids_to_remove = get_subject_details_of_study(study_name, data)
        context['d'] = eval(sorted_json)
        context['subject_details']= ids_to_remove

        logger.info("display_study::end::%s",study_name)
    except IOError as ie:
        context['error_message'] = "File not Found"
    except KeyError as ke:
        context['error_message'] = "Parsing Error"
    except EmptyDataError:
        context['error_message'] = "No columns to parse from file"
    except Exception as e:
        logger.info("get_all_study_details::: Exception occurred %s",e)
    return context

def get_modified_json_form_csv(data):
    modified_data = {}
    temp_str = ""
    grouped_subjects_list = []
    for obj in data:
        temp_str = obj['subject_name'][:-2]
        obj["group_name"] = temp_str
        if temp_str in modified_data.keys():
            value = modified_data[temp_str]  # add the object to the exisiting dict
            value.append(obj)
            modified_data[temp_str] = value
        else:
            grouped_subjects_list.append(obj)
            modified_data[temp_str] = grouped_subjects_list
            grouped_subjects_list = []
    count = len(modified_data.keys())
    sorted_json = json.dumps(modified_data, sort_keys=True)
    return sorted_json, count

def get_latest_received_study_sensor_details(study_name):
    """
    Method for retreiving latest_received_study_sensor_details

    """
    filtered_list= []
    data = parse_get_dashboard_csv(study_name)
    try:
        for row in data:
            for key, value in row.items():
                if 'last_time_received' in key and value != None:
                    if current_date == value.split(" ")[0]:
                        filtered_list.append(key.split(" ")[0])
    except Exception as e:
        logger.info("get_latest_received_study_sensor_details::Exception occurred %s",e)
    return filtered_list


def calculate_stats_of_number_of_subjects(study_name, number_of_subjects):
    """
    Method for calculate_stats_of_number_of_subjects

    """
    stats_json = {}
    temp_json = {'removed': [], 'completed': [], 'leftstudy': [], 'instudy': []}
    df = read_study_df(study_name)

    if not df.empty:
        # parsing the CSV in json format.
        json_records = df.reset_index().to_json(orient='records')
        data = json.loads(json_records)
        for obj in data:
            if obj["status_code"] == 1:
                temp_json['leftstudy'].append(obj['subject_name'])
            elif obj["status_code"] == 2:
                temp_json['completed'].append(obj['subject_name'])
            elif obj["status_code"] == 3:
                temp_json['removed'].append(obj['subject_name'])
            else:
                temp_json['instudy'].append(obj['subject_name'])

        stats_json['leftstudy'] = len(temp_json['leftstudy'])
        stats_json['leftstudy_percentage'] = round(100 * (stats_json['leftstudy'] / number_of_subjects), 1)
        stats_json['instudy'] = len(temp_json['instudy'])
        stats_json['instudy_percentage'] = round(100 * (stats_json['instudy'] / number_of_subjects), 1)
        stats_json['completed'] = len(temp_json['completed'])
        stats_json['completed_percentage'] = round(100 * (stats_json['completed'] / number_of_subjects), 1)
        stats_json['removed'] = len(temp_json['removed'])
        stats_json['removed_percentage'] = round(100 * (stats_json['removed'] / number_of_subjects), 1)

    return stats_json


def get_subject_details_of_study(study_name, data):
    """
    Method for calculate_stats_of_number_of_subjects

    """
    subject_details = {}
    list_of_ids = []
    for obj in data:
        subject_json = get_subject_details(study_name, obj['subject_name'])
        subject = Subject(obj, subject_json)
        subject.missing_data = True if subject.date_left_study == "none" else False
        if subject.status == 0:
            list_of_ids.append(
                subject.subject_name + constants.sep + subject.app + constants.value_sep + str(subject.missing_data))
    subject_details['ids_to_be_removed'] = sorted(list_of_ids)
    return subject_details

def update_number_of_subjects(study_name, total_count):
    """
    Method for update_number_of_subjects

    """
    study_json = open_study_json(study_name)
    study_json[constants.key_name_number_of_subjects] = total_count
    save_study_json(study_name, study_json)


def update_study_details(study_name, values_obj):
    """
    update a study (values to study.json file)

    :param study_name:
    :param values_obj:
    :return:
    """

    study_json = open_study_json(study_name)
    # create backup json wtih versioning
    create_backup_json_file(study_name, study_json)
    # find the differencec between both json and 
    # add new values to the original json object
    #logger.info("update_study_details %s",values_obj)
    study_json['duration'] = values_obj['duration']
    study_json['description'] = values_obj['description']
    study_json['is_test'] = values_obj['is_test']
    study_json['images'] = values_obj['images']
    if 'sensor_list' in values_obj:
        study_json['frequency'] = values_obj['frequency']
        study_json['sensor_list'] = values_obj['sensor_list']
        if 'task_list' in values_obj and len(values_obj['task_list']) != 0:
            task_list = []
            for task in values_obj['task_list']:
                if validate_empty(task['task_name']):
                    task_list.append(task)
            study_json['task_list'] = task_list
        else:
            study_json['task_list'] = []
        study_json['sensor_list_limited'] = values_obj['sensor_list_limited']
        if len( values_obj['task_list']) ==0 and len(values_obj['sensor_list_limited'])  == 0:
            study_json[constants.field_name_labeling] = 0

        if len( values_obj['task_list']) > 0 and len(values_obj['sensor_list_limited'])> 0:
            study_json[constants.field_name_labeling] = 1

        if len( values_obj['sensor_list']) > 0 and len(values_obj['task_list'])> 0 :
            study_json[constants.field_name_labeling] = 2

        if len( values_obj['sensor_list']) > 0 and len(values_obj['sensor_list_limited'])> 0 :
            study_json[constants.field_name_labeling] = 3
    #to add ema to already exisiting study
    if 'survey' in values_obj:
        logger.info("update_study_details:: survey %s",values_obj['survey'])
        if type(values_obj['survey']) == int :
            study_json['survey'] = generate_survey_json_for_download(values_obj['survey'])
        else:
            study_json['survey'] = values_obj['survey']
    study_json["version"] = study_json["version"] + 1
    #logger.info("update_study_details:: study_json %s",study_json)
    save_study_json(study_name, study_json)
    
    return study_json


def update_survey_details(study_name, values_obj, is_question):
    """
    update a study (values to study.json file)

    :param study_name:
    :param values_obj:
    :param is_question:
    :return:
    """
    study_json = open_study_json(study_name)
    # initially update the json
    if is_question:
        question_id = values_obj['id']
        # get the object from the study json and update with recent values
        for question in study_json['survey']['questions']:
            if question['id'] == int(question_id):
                question['title'] = values_obj['title']
                question['subText'] = values_obj['subText']
                question['frequency'] = values_obj['frequency']
                question['clockTime'] = values_obj['clockTime']
                question['nextDayToAnswer'] = values_obj['nextDayToAnswer']
                question['category'] = values_obj['category']
                question['imageURL'] = values_obj['imageURL']
                question['url'] = values_obj['url']
                question['questionType'] = values_obj['questionType']
                question['deactivateOnAnswer'] = values_obj['deactivateOnAnswer']
                question['deactivateOnDate'] = values_obj['deactivateOnDate']
    else:
        study_json['survey']['title'] = values_obj['title']
        study_json['survey']['description'] = values_obj['description']
        study_json['splitbyCategory'] = values_obj['splitbyCategory']
        study_json['scrolling'] = values_obj['scrolling']
        study_json['survey']['topN'] = values_obj['topN']
    save_study_json(study_name, study_json)
    return True


def close_study(study_name, user):
    """
    close a study (moves it to archive folder)

    :param study_name:
    :param user:
    :return:
    """
    response = False
    archived_study_path = os.path.join(config.archive_folder, study_name)
    os.makedirs(archived_study_path)
    os.rename(os.path.join(config.studies_folder, study_name), os.path.join(archived_study_path, study_name))

    study_csv = config.csv_prefix + study_name + '.csv'
    study_csv_path = os.path.join(config.storage_folder, study_csv)
    if os.path.isfile(study_csv_path):
        os.rename(study_csv_path, os.path.join(archived_study_path, study_csv))

    # update the closed boolean in the database
    context = {'msg': "study_name is closed"}
    logger.info("Study    %s is closed by  %s", study_name, user.username)
    response = close_study_model(study_name)

    if response:
        logging.info("Failed to update database")

    return get_all_study_details(user)


def zip_unused_sheets(study_name):
    """
    zip all unused study sheets in order to download it later

    :param study_name:
    :return:
    """
    # logging.info("Create Zip")
    os.chdir(config.dash_folder)
    try:
        study_df = read_study_df(study_name)
        enrolled_subject_list = get_user_list(study_df)
        logger.info(enrolled_subject_list)
    except (FileNotFoundError, KeyError, studyexceptions.EmptyStudyTableException):
        enrolled_subject_list = []
    sheets_path = os.path.join(config.app_study_folder, study_name, config.sheets_folder)
    zip_path = os.path.join(config.app_study_folder, study_name, config.zip_file)
    if os.path.isfile(zip_path):
        os.remove(zip_path)

    all_subjects_pdfs = np.array(os.listdir(sheets_path))
    enrolled_subjects_pdfs = np.array([enrolled_subject + '.pdf' for enrolled_subject in enrolled_subject_list])
    not_enrolled_subjects_pdfs = [os.path.join(sheets_path, not_enrolled_subject) for not_enrolled_subject in
                                  np.setdiff1d(all_subjects_pdfs, enrolled_subjects_pdfs)]

    os.system('zip ' + zip_path + ' ' + ' '.join(not_enrolled_subjects_pdfs))
    context = {'msg': "download unused files"}
    return context



