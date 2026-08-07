"""Shared application constants.

Moved out of jdash.apps so AppConfig only contains app configuration.
"""

post_method = "POST"
get_method = "GET"
logging_date_format = "%H:%M:%S"
date_format = '%d%m%Y'
timezone= 'Europe/Berlin'
encoding = 'utf-8'
timezone= 'Europe/Berlin'
# end points constants

end_point_for_login = "login/"
end_point_for_logout = "logout/"
end_point_for_contactus = "contactus/"
end_point_for_add = "add/"
end_point_for_edit = "edit/<str:study_name>"
end_point_for_details = "details/<str:study_name>"
end_point_for_details_with_id = "details/<str:study_name>/<str:id_type>"
end_point_for_createsurvey = "createsurvey/"
end_point_for_edit = "edit/<str:study_name>/editsurvey"
end_point_for_delete = "delete_subject"
end_point_for_close = "close/<str:study_name>"
end_point_for_download = "download/<str:arg>/"
end_point_for_jlytics = "jlytics/"

# url names for each end point
url_name_for_home = "home"
url_name_for_login = "login"
url_name_for_logout = "logout"
url_name_for_password_reset = "password_reset"
url_name_for_password_reset_done = "password_reset_done"
url_name_for_password_reset_confirm = "password_reset_confirm"
url_name_for_password_reset_complete = "password_reset_complete"
url_name_for_contact_email = "contact_email"
url_name_for_add_study = "add_study"
url_name_for_edit_study = "edit_study"
url_name_for_qc_study = "qc_study"
url_name_for_study_audit = "study_audit"
url_name_for_survey_audit = "survey_audit"
url_name_for_details = "details"
url_name_for_create_survey = "create_survey"
url_name_for_manage_question = "manage_question"
url_name_for_duplicate_survey = "duplicate_survey"
url_name_for_duplicate_question = "duplicate_question"
url_name_for_delete_survey = "delete_survey"
url_name_for_delete_question = "delete_question"
url_name_for_edit_survey = "edit_survey"
url_name_for_create_categories = "create_categories"
url_name_for_delete_subject = "delete_subject"
url_name_for_close = "close"
url_name_for_download = "download"
url_name_for_download_dataset = "download_dataset"
url_name_for_download_json = "download_json"
url_name_for_download_ics = "download_ics"
url_name_for_generate = "generate"
url_name_for_survey = "survey"
url_name_for_analytics = "analytics"
url_name_for_list_of_studies = "studies"
url_name_for_delete_subject_data = "delete_subject_data"

# html names

login_page = "login.html"
password_reset_form_page = "password_reset/form.html"
password_reset_done_page = "password_reset/done.html"
password_reset_confirm_page = "password_reset/confirm.html"
password_reset_complete_page = "password_reset/complete.html"
password_reset_email = "password_reset/email.html"
password_reset_subject = "password_reset/user.txt"
details_page = "study/details.html"
home_page = "index.html"
create_study_page = "study/create_study.html"
sop_list_of_study_page = "study/sop_list_study.html"
study_audit_page = "study/study_audit_list.html"
survey_audit_page = "survey/survey_audit_list.html"
create_survey_page = "survey/create_survey.html"
create_question_page = "survey/create_question.html"
edit_question_page = "survey/edit_question.html"
edit_study_page = "study/edit_study.html"
edit_survey_page = "survey/edit_survey.html"
survey_page = "survey/survey_list.html"
analytics_details_page = "analytics/view_analytics.html"
error_page = "error.html"
contact_us = "contact_us.html"
delete_subject = "subject/delete_subject.html"
success = "success.html"
input_email = "email/input_email.html"
download_link = 'email/download_link.html'
code_verification = 'email/code_verification.html'
contact_us_admin = 'email/contacts_us_admin.html'
delete_subject_admin = 'email/delete_subject_admin.html'
download_confirm = 'email/download_data_confirm.html'

 # session variables
session_key_username = "username"
session_key_groupname = "groupname"
session_key_studies = "studies"
session_key_studies_stats = "studies_stats"
session_key_survey_details = "survey_details"
session_key_studies_ema = "studies_ema"
session_key_old_ema = "old_ema_studies"
session_key_user_details = "user_details"
session_key_display_studies_obj = "display_studies_obj"
session_key_list_studies = "list_studies"
session_key_json_meta = "study_json_meta"
session_key_survey_list = "survey_list"
session_key_email = "email"
session_key_first_name = "first_name"
session_key_last_name = "last_name"
## Json key constants ####
key_name_app = "app"
key_name_id = "id"
key_name_version = "version"
key_name_type = "type"
key_name_study_name = "study_name"
key_name_number_of_subjects = "number_of_subjects"
key_name_subject_details = "subject_details"
key_name_ids_to_be_removed = "ids_to_be_removed"
key_name_sensor_list = "sensor_list"
key_name_current_sensor_list = "current_sensor_list"
key_name_meta_data = "meta_data"
key_name_survey = "survey"
key_name_task_list = "task_list"
key_name_category_list = "category_list"
key_name_count = "count"
key_name_created_date = "createdDate"
key_name_study_title = "title"
key_name_survey_description= "description"
key_name_survey_topN = "topN"
key_name_subject_name = "subject_name"
key_name_status_code = "status_code"
key_name_success_message = "success_message"
key_name_error_message = "error_message"
key_study_name_json = "name"
# response json 'context'  key name constants
key_name_new_subjects_form = "new_subjects_form"
key_name_remove_subjects_form = "remove_subjects_form"
key_name_notification_form = "notification_form"
key_name_delete_subject_form = "delete_subject_form"
key_name_login_form = "login_form"
key_name_task_formset = "task_formset"
key_name_wbdevice_formset = "wbdevice_formset"
key_name_wbdevice_sensor_formset = "wbdevice_sensor_formset"
key_name_study_meta = "study_meta"
key_name_survey_form = "survey_form"
key_name_survey_jsonform = "json_form"
key_name_category_formset = "category_formset"
key_name_category_form = "category_form"
key_name_study_form = "study_form"
key_name_answer_formset = "answer_formset"
key_name_answer_text_form = "answer_text_form"
key_name_study_form = "study_form"
key_name_question_form = "question_form"
key_name_answer_form = "answer_form"
key_name_contact_form = "contact_form"
key_name_json_meta = "json_meta"
key_name_study_name = "study_name"
key_name_survey_form = "survey_form"
key_name_is_survey = "is_survey"
key_name_stats = "stats"
key_name_info_text = "info_text"
key_name_survey_id = "survey_id"
key_name_question_id = "question_id"
key_name_survey_title= "survey_title"
key_name_questions = "questions"
key_name_question_details = "question_details"
key_name_categories = "categories"
key_name_topN = "topN"
key_name_survey_help_text = "survey_help_text"
key_name_question_help_text = "question_help_text"
key_name_category_help_text = "category_help_text"
key_name_study_help_text = "study_help_text"
key_name_collect_subject_id_flag = "collect_subject_id_flag"
key_name_collect_flag = "collect_flag"
key_name_survey_list = "survey_list"
key_name_text_message = "text_message"
key_name_total_count = "total_count"
key_name_session_id = "session_id"
key_name_sortId = "sortId"
key_name_id = "id"
key_name_test_list = "test_list"
key_name_study = "study"
key_name_collect_subject_id_flag = "collect_subject_id_flag"
key_name_collect_flag = "collect_flag"
key_name_categoryTitle = "categoryTitle"
key_name_categoryValue = "categoryValue"
key_name_didSubjectAsk = "didSubjectAsk"
# form data field name
field_name_name = "name"
field_name_images = "images"
field_name_survey = "survey"
field_name_images = "images"
field_name_subject_to_remove = "subject_to_remove"
field_name_subjectId = "subjectId"
field_name_number_of_subjects = "number_of_subjects"
field_name_images_zip_file = "images_zip_file"
field_name_username = 'username'
field_name_password = 'password'
field_name_message_title = "message_title"
field_name_message_text = "message_text"
field_name_receivers = "receivers"
field_name_question_id = "question_id"
field_name_answer_id = "answer_id"
field_name_frequency = "frequency"
field_name_labeling = "active_labeling"
field_name_sensor_list = "sensor_list"
field_name_is_test = "is_test"
field_name_sensor_list_limited = "sensor_list_limited"
field_name_email = "email"
field_name_reason = "reason"
field_name_user_email = "user_email"
field_name_survey_id = "survey_id"
field_name_id_value = "id_value"
field_name_json_file = "json_file"
field_name_timezone= "timezone"
field_name_test_case_flags= "test_case_flags"
field_name_clockTime= "clockTime"
field_name_clockTime_start= "clockTime_start"
field_name_clockTime_end= "clockTime_end"
field_name_activate_question= "activate_question"
field_name_deactivate_question= "deactivate_question"
field_name_activation_condition= "activation_condition"
field_name_deactivation_condition= "deactivation_condition"
field_name_user_email = "user_email"
field_name_survey_id = "survey_id"
field_name_json_file = "json_file"
field_name_timezone= "timezone"
field_name_test_case_flags= "test_case_flags"
field_name_clockTime= "clockTime"
field_name_clockTime_start= "clockTime_start"
field_name_clockTime_end= "clockTime_end"
field_name_activate_question= "activate_question"
field_name_deactivate_question= "deactivate_question"
field_name_activation_condition= "activation_condition"
field_name_deactivation_condition= "deactivation_condition"
field_name_active = "active"
field_name_mandatory = "mandatory"
field_name_answer = "answer"
field_name_category = "category"
field_name_title = "title"
field_name_questionType = "questionType"
field_name_text = "text"
field_name_value = "value"
field_name_defaultValue = "defaultValue"
field_name_stepSize = "stepSize"
field_name_minVal = "minVal"
field_name_maxVal = "maxVal"
field_name_minValue = "minValue"
field_name_maxValue = "maxValue"
field_name_minText = "minText"
field_name_maxText = "maxText"
field_name_answerSubText = "answerSubText"
field_name_answerSortId = "answerSortId"
field_name_db_id = "db_id"
# name constants from templates
button_name_contact_message = "contact_message"
button_name_send_notification = "send_notification"
button_name_create_subjects = "create_subjects"
button_name_remove_subjects = "remove_subjects"
button_name_update_study = "update_study"
button_name_create_survey = "create_survey"
button_name_manage_categories = "manage_categories"
button_name_copy_question = "copy_question"
button_name_update_survey_info = "update_survey_info"
button_name_upload_survey = "upload_survey"
button_name_delete_survey = "delete_survey"
button_name_add_question = "add_question"
button_name_edit_question = "edit_question"
button_name_update_survey = "update_survey"
button_name_update_question = "update_question"
button_name_update_question_sort = "update_question_sort"
button_name_delete_subject_data = "delete_subject_data"
button_name_add_answer = "add_answer"
button_name_download_data_confirm = "verifyCode"
button_name_delete_question = "delete_question"
button_name_remove_question = "remove_question"
button_name_new_question = "new_question"
button_name_update_test_flags = "update_test_flags"
# Other constants values used
underscore_seperator = "_"
max_subjects_exp = 5
number_of_activations = 4
timestamp_format = "%Y-%m-%d %H:%M:%S"
sep = ':'
value_sep = ";"
remove_status_code = 3
passive_monitoring = 'passive_monitoring'
ema = 'ema'
main = 'main'
modalities = [ema, main]
suffix_per_modality_dict = {
    ema: '_ema',
    main: ''
}

group_name_administrator = "administrator"
group_name_investigator = "Investigator"
group_name_viewer = "Viewer"

group_mapping = {
"administrator": "administrator",
"Investigator": "Investigator",     
}
default_group = "Viewer"

# Constants used for filter options and custom codes
accelerometer = "accelerometer"
activity = "activity"
gyroscope = "gyroscope"
location = "location"
lockUnlock = "lockUnlock"
voice = "voice"
rotation_vector = "rotation_vector"
active_labeling = "active_labeling"
application_usage = "application_usage"
barometer = "barometer"
gravity_sensor = "gravity_sensor"
magnetic_sensor = "magnetic_sensor"
linear_acceleration = "linear_acceleration"
pedometer = "pedometer"
# response header constants
zip_extension = '.zip'
pdf_extension = ".pdf"
ics_extension = ".ics"
json_extension = ".json"
zip_content_type = "application/zip"
pdf_content_type = "application/pdf"
ics_content_type = "text/calendar"
sensor_list = {
    ema: "ema",
    accelerometer: "ac",
    activity: 'at',
    gyroscope: 'gy',
    location: 'lo',
    lockUnlock: 'ln',
    voice: 'vo',
    rotation_vector: 'ro',
    active_labeling: 'al',
    application_usage: 'au',
    barometer: 'ba',
    gravity_sensor: 'gs',
    magnetic_sensor: 'ms',
    linear_acceleration: 'la',
    pedometer: 'pd'
}

 ## UI dropdown constants ####
RECORDING_FREQUENCIES = [
    (0, ""),
    (50, "50 hz"),
    (100, "100 Hz"),
    (150, "150 Hz"),
    (200, "200 Hz")
]

SENSORS_LIST = [
    ("accelerometer", "accelerometer"),
    ("activity", "activity"),
    ("application_usage", "application usage"),
    ("barometer", "barometer"),
    ("gravity_sensor", "gravity sensor"),
    ("gyroscope", "gyroscope"),
    ("location", "location"),
    ("magnetic_sensor", "magnetic sensor"),
    ("rotation_vector", "rotation vector"),
    ("linear_acceleration", "linear acceleration"),
    ("lockUnlock", "lockUnlock"),
    ("voice", "voice"),
    ("pedometer", "pedometer")

]

SENSORS_LIST_DB = [
    ("", ""),
    ("accelerometer", "accelerometer"),
    ("activity", "activity"),
    ("application_usage", "application usage"),
    ("barometer", "barometer"),
    ("gravity_sensor", "gravity sensor"),
    ("gyroscope", "gyroscope"),
    ("location", "location"),
    ("magnetic_sensor", "magnetic sensor"),
    ("rotation_vector", "rotation vector"),
    ("linear_acceleration", "linear acceleration"),
    ("lockUnlock", "lockUnlock"),
    ("voice", "voice"),
    ("pedometer", "pedometer")

]

QUESTION_TYPES = (
    (0, 'Instruction for questions'),
    (1, 'Single Choice'),
    (2, 'Multiple Choice'),
    (3, 'Sliding'),
    (4, 'Free Text'),
    (5, 'Free Number'),
    (6, 'Time'),
    (7, 'Date'),
    (8, 'Time and Date'),
    (9, 'Duration'),
    (10, 'Location'),
    (11, 'Consent')
)

LABELLING = [
    (0, "No labeling "),
    (1, "Active labeling"),
    (2, "Manual active labeling"),
    (3, "Partial active labeling")
]

SCROLLING_CHOICES = [
    ('H', "Horizontal"),
    ('V', "Vertical")
]

TEST_TYPE_CHOICES = [
    ('Notification', 'Notification'),
    ('Sensor', 'Sensor'),
    ('EMA', 'EMA'),
    ('Subject', 'Subject'),
]

# messages

only_alphanumeric = "Only alphanumeric characters are allowed in study label."

no_data = "No data sent for 2 days"
multiple_qr = "Multiple QR Codes of one user active"
duration_reached_left = "Study duration reached, not left"
duration_reached = "Study duration reached, left"
left_early = "Left study too early"

no_sensor_data = "No sensor data received for 2 days"
sensor_data_active = "Sensor active"
no_sensor_duration_reached = "Study duration reached, left"
no_sensor_left_early = "Left study too early"
no_sensor_duration_exceeded = "Study duration exceeded while subject is still in study"
no_sensor_not_received = "No sensor data received yet"
