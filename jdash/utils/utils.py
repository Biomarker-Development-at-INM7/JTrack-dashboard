import json, logging, os
from django.db.models import Q
from datetime import date,datetime
from django.utils import timezone
from operator import itemgetter
from jdash.config import constants as constants
from jdash.interface.session_manager import SessionManager
from jdash.utils.fileutils import get_json_data,read_study_df,parse_get_dashboard_csv
from jdash.services.subject import Subject

current_date = timezone.now().strftime('%Y-%m-%d')
logger = logging.getLogger("django")

def study_name_user_id(value):
    bufferdString = ""
    strArray = value.split(constants.underscore_seperator)
    #check for last occurence of _ and get the study name
    for i in range(len(strArray) -1):
        bufferdString = bufferdString + strArray[i] 
        bufferdString = bufferdString + constants.underscore_seperator
    return bufferdString[:-1] 


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
        subject_json = Subject.load_details(study_name, obj['subject_name'])
        subject = Subject(obj, subject_json)
        subject.missing_data = True if subject.date_left_study == "none" else False
        if subject.status == 0:
            list_of_ids.append(
                subject.subject_name + constants.sep + subject.app + constants.value_sep + str(subject.missing_data))
    subject_details['ids_to_be_removed'] = sorted(list_of_ids)
    return subject_details

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




def get_survey_list(session_key):
    """
    Retrieves a list of surveys associated with a given session key.
    This function fetches survey data from session-specific information and
    processes it into a structured list of dictionaries containing survey details.
    Args:
        session_key (str): The session key used to retrieve session-specific data.
    Returns:
        list: A list of dictionaries, where each dictionary represents a survey with
              the following keys:
              - 'id': A placeholder ID for the survey (default is '999').
              - constants.key_name_study_title: The title of the study.
              - constants.key_name_study_name: The name of the study extracted from the JSON data.
              - constants.key_name_survey_description: A description of the survey.
              - constants.key_name_survey_topN: The topN value from the survey data, or -1 if not present.
        str: An error message ("Unknown Exception occurred") if an exception is raised.
    Raises:
        Logs any exceptions that occur during the process and returns a generic error message.
    """
    logger.info("get_survey_list::start")
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
                survey["category_names"] = ", ".join(
                    category.get("categoryTitle", "")
                    for category in data.get(constants.key_name_survey, {}).get(constants.key_name_categories, [])
                    if category.get("categoryTitle")
                )
                total_list.append(survey) 
            return total_list
    except Exception as e:
        logger.info("Exception occured while fetching from survey files: %s",e)
        return "Unknown Exception occured"
    
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
            "title": obj['title'].encode(constants.encoding).decode(constants.encoding),
            "description": obj['description'].encode(constants.encoding).decode(constants.encoding),
            "topN": obj['topN'],
            "splitbyCategory" : obj['splitbyCategory'],
            "scrolling" : obj['scrolling'],
            # Handle datetime or other complex types explicitly
            "createdDate": obj['createdDate'].strftime('%Y-%m-%d') if isinstance(obj['createdDate'], date) else None,
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
            "clockTime" : question_data['clockTime'] if question_data['clockTime'] is not None else 0,
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
            "categoryTitle": category_data['categoryTitle'].encode(constants.encoding).decode(constants.encoding),
            "categoryValue" : category_data['categoryValue'],
            "didSubjectAsk" : category_data['didSubjectAsk']
        }
        result.append(item)
    return json.dumps(result)

def question_db_list_serializer(value): 
    '''
    Serializer for the question list
    '''
    if value == "":
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
    #if isinstance(question['activate_question'], list):
    #    question['activate_question'] =question_string_serializer(question['activate_question'])
    #if isinstance(question['deactivate_question'], list):
    #    question['deactivate_question'] = question_string_serializer(question['deactivate_question'])
    # Keep activate/deactivate question references as lists.

    # Only clockTime fields are serialized to strings for legacy study.json format.
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
        logger.info("question_serializer::question_data: %s", question_data)
        clocktime_str = question_data['clockTime']        
        clocktime_start_str = ""
        clocktime_end_str = ""

        activate_question_list = normalize_question_refs(question_data.get('activate_question'))
        deactivate_question_list = normalize_question_refs(question_data.get('deactivate_question'))

        if question_data['clockTime_start'] not in (None, ""," ", []):           
            clock_start_raw = question_data['clockTime_start']                   
            logger.info("question_serializer:start_str %s %s",clock_start_raw,type(clock_start_raw))
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
                        clocktime_end_str = str(question_data['clockTime_end'][0])    
        else:                                                                    
             clocktime_str = 1                                                    
        logger.info("question_serializer:clockTimes %s %s",clocktime_str,clocktime_start_str) 

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
            "activate_question" : activate_question_list,
            "deactivate_question" : deactivate_question_list,
            "deActivate_question": deactivate_question_list,
            "activation_condition" : question_data['activation_condition'],
            "deactivation_condition" : question_data['deactivation_condition'],
            "deActivation_condition": question_data['deactivation_condition'],
            "clockTime_timezone" : question_data['clockTime_timezone'] 
        }
        result.append(item)
    return json.dumps(result)

def generete_survey_notification_obj(survey, study_duration):
    """
    Generates a mapping from day numbers to clockTime values for a survey.
    """
    days_obj = {}
    for quest in survey["questions"]:
        frequency = quest.get("frequency", 0)
        if frequency == 0:
            continue  # skip invalid frequency

        start = quest.get("startOnDay", 0)
        end = quest.get("endOnDay", study_duration)

        # override end if deactivateOnDate is given
        if "deactivateOnDate" in quest:
            if quest["deactivateOnDate"] is not None and quest["deactivateOnDate"] != 0:
                end = quest["deactivateOnDate"]

        clock_time = quest.get("clockTime")
        if clock_time is None:
            continue  # skip adding if clockTime is not set

        for i in range(start, end, frequency):
            if i not in days_obj:
                days_obj[i] = []
            if clock_time not in days_obj[i]:
                days_obj[i].append(clock_time)

    return days_obj

def create_sql_statements_for_quality_control_tests(study_data, output_sql_file,study_id):
    """
    Function to create SQL statements for quality control tests
    """
    logger.info("Creating SQL statements for quality control tests %s", study_data)
    tested_by_admin = False
    tested_by_owner = False
    
    def _escape(value):
        return str(value).replace('"', '""')

    def _write_case(sql_file, testcase_id, test_type, description, steps, expected_outcome):
        sql = f"""
        INSERT INTO jdash_qualitycontroltests (
            testcase_id, test_type, description, steps, expected_outcome,
            tested_by_admin, tested_by_owner, study_id
        ) VALUES (
            "{_escape(testcase_id)}", "{_escape(test_type)}", "{_escape(description)}",
            "{_escape(steps)}", "{_escape(expected_outcome)}",
            {int(tested_by_admin)}, {int(tested_by_owner)}, {study_id}
        );
        """
        sql_file.write(sql.strip() + "\n")

    with open(output_sql_file, 'w', encoding="utf-8") as sql_file:
        _write_case(
            sql_file,
            "DATA-01",
            "Data",
            "Validate real-time monitoring of data",
            "1. Access study view page. 2. Verify live batch data updates for sensors and EMA(if necessary).",
            "Data should update in real-time on the dashboard.",
        )
        _write_case(
            sql_file,
            "DATA-02",
            "Data",
            "Verify data export functionality",
            "1. Export study data. 2. Check for link to download and verification code email received",
            "Exported data should match sensors and other necessary identifiers",
        )
        _write_case(
            sql_file,
            "SUB-01",
            "Subject",
            "Verify participant enrollment process",
            "1. Scan QR code from downloaded Activation pdf.\n 2. Verify subject can access the JTrack successfully. ",
            " Participant information should be correctly saved during enrollment.",
        )

        survey = study_data.get("survey")
        if isinstance(survey, dict) and "questions" in survey:
            for index, question in enumerate(survey.get("questions", [])):
                _write_case(
                    sql_file,
                    f"EMA-{index}",
                    "EMA",
                    question.get("title", ""),
                    "",
                    "Check the data stored variable",
                )

        for index, sensor in enumerate(study_data.get("sensor_list", [])):
            for platform_code, platform_label in (("AND", "Android"), ("IOS", "iOS")):
                _write_case(
                    sql_file,
                    f"PSEN-{platform_code}-{index}",
                    "Sensor",
                    f"Verify passive sensor data is logged correctly for {sensor} on {platform_label}",
                    f"1. Simulate {sensor} for a subject on {platform_label}. 2. Check if {sensor} json is generated.",
                    f"{sensor} data from {platform_label} should appear in json accurately with timestamps.",
                )

        for index, sensor in enumerate(study_data.get("sensor_list_limited", [])):
            _write_case(
                sql_file,
                f"ASEN-{index}",
                "Sensor",
                "Verify that sensor data is logged correctly",
                f"1. Simulate {sensor} for a subject. 2. Check if {sensor} json is generated. ",
                f"{sensor} data should appear in json accurately with timestamps. ",
            )

        for device_index, wearable in enumerate(study_data.get("wearables", [])):
            device_name = (
                wearable.get("sensorname")
                or wearable.get("manufacturer")
                or wearable.get("model")
                or "wearable device"
            )

            for sensor_index, sensor in enumerate(wearable.get("sensors", [])):
                sensor_label = sensor.get("wearable_sensor", "wearable sensor")
                for platform_code, platform_label in (("AND", "Android"), ("IOS", "iOS")):
                    _write_case(
                        sql_file,
                        f"WDEV-{platform_code}-{device_index}-{sensor_index}",
                        "Sensor",
                        f"Verify {device_name} wearable data is logged correctly for {sensor_label} on {platform_label}",
                        f"1. Simulate {device_name} {sensor_label} collection on {platform_label}. 2. Check if {sensor_label} json is generated.",
                        f"{device_name} {sensor_label} data from {platform_label} should appear in json accurately with timestamps.",
                    )
            
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

    if question_data[constants.field_name_activation_condition] is None:
        question_data[constants.field_name_activation_condition] = ""
        
    if question_data[constants.field_name_deactivation_condition] is None:
        question_data[constants.field_name_deactivation_condition] = ""

    # Legacy compatibility:
    # if an older survey only has clockTime filled, convert it into a single
    # activation time when no explicit start/end windows are present.
    if question_data[constants.field_name_clockTime] > 0 \
        and len(question_data[constants.field_name_clockTime_start]) == 0 \
        and len(question_data[constants.field_name_clockTime_end]) == 0:
        question_data[constants.field_name_clockTime_start].append(
            question_data[constants.field_name_clockTime]
        )

    # if clockTime_start has one value and clockTime_end is empty, add clockTime_start value to clockTime
    if len(question_data[constants.field_name_clockTime_start]) == 1 \
        and len(question_data[constants.field_name_clockTime_end]) == 0:
        question_data[constants.field_name_clockTime] = question_data[constants.field_name_clockTime_start][0]


    # if clockTime_start has more than one value, set clockTime = 1 assuming  clockTime_end has same length has clockTime_start
    if len(question_data[constants.field_name_clockTime_start]) > 1 :
        question_data[constants.field_name_clockTime] = 0

    return question_data

def normalize_question_refs(value):
    """
    Normalize question references to list[int].

    Accepts:
    - [5]
    - ["5", "6"]
    - "5"
    - "5,6,7"
    - "5;6;7"
    - ""
    - None
    """
    if value in (None, "", []):
        return []

    if isinstance(value, list):
        result = []
        for item in value:
            if item in (None, ""):
                continue
            result.append(int(item))
        return result

    if isinstance(value, int):
        return [value]

    if isinstance(value, str):
        value = value.replace(";", ",")
        return [
            int(part.strip())
            for part in value.split(",")
            if part.strip()
        ]

    return []

