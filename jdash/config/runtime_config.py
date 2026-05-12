import os

from django.conf import settings


studies = 'studies'
archive = 'archive'
users = 'users'
images = 'image_resources'
studies_bids = 'studies_bids'
storage_folder = settings.STORAGE_FOLDER
studies_folder = os.path.join(storage_folder, studies)
archive_folder = os.path.join(storage_folder, archive)
users_folder = os.path.join(storage_folder, users)
images_folder = os.path.join(storage_folder, images)
txt_prefix = 'jtrack_delete_subject_'
csv_prefix = 'jutrack_dashboard_'
sheets_folder = 'Subject-Sheets'
qr_folder = 'QR-Codes'
zip_file = 'sheets.zip'
app_study_folder = 'Studies'
download_folder = 'downloads'
analytics_outputs_folder = "outputs"
analytics_storage_folder = os.path.join('/mnt/jutrack_data', studies_bids)
max_subjects_exp = 5
number_of_activations = 4
ema = 'ema'
main = 'main'
update_notification_log_file = os.path.join(storage_folder, 'standalone', 'update_output.log')
#os.makedirs(os.path.dirname(update_notification_log_file), exist_ok=True)
update_json_survey_script_path = os.path.join(storage_folder, 'standalone', 'update_json.py')
download_zip_files_log = 'download_zip_files_log.csv'
firebase_content_type = 'application/json'
SCOPES = ['https://www.googleapis.com/auth/firebase.messaging']
juseless_download_script_path = os.path.join(settings.JUSELESS_SCRIPT_FOLDER, 'download.py')
