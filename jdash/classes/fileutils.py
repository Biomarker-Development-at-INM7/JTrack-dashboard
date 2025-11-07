import json, os, csv,shutil,logging,re
from datetime import datetime, date
import stat,subprocess
import numpy as np
import pandas as pd
from jdash.apps import jdashConfig as config
from jdash.apps import constants as constants
logger = logging.getLogger("django")
current_date = datetime.strftime(datetime.now().astimezone(),'%Y%m%d%H%M%S')

def get_notification_json_for_study(study_name):
    json_path = os.path.join(config.storage_folder, "standalone", 'json_of_days_for_push_notification.json')
    with open(json_path, 'r') as f:
        cfg = json.load(f)
    return cfg[study_name]

def get_study_name_from_subject_id(subject_id):
    """
    Method to parse meta data json of  all studies

    :param study_directories:
    :return:
    """
    subject_json_path = os.path.join(config.users_folder, subject_id + ".json")
    with open(subject_json_path, 'r') as f:
        cfg = json.load(f)
    return cfg["studyId"]

#create csv for loggin the downlaoded request
def create_download_file_log(row):
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """
    csv_filepath = os.path.join(config.storage_folder,config.download_folder,config.download_zip_files_log)
    # Check if the file exists to decide on writing the header
    file_exists = os.path.isfile(csv_filepath)
    with open(csv_filepath, mode='a', newline='',encoding='utf-8') as file:
        writer = csv.writer(file)
        # If the file does not exist, write the header first
        if not file_exists:
            writer.writerow(['dataset','FirstName', 'Email', 'Link',  'Status','Requested','Emailed','Downloaded'])
        
        # Write the data row
        writer.writerow(row)

#updating the status of the downloaded status into csv file
def updated_status():
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """
    updated_rows=[]
    csv_file_path = os.path.join(config.storage_folder,config.download_folder,config.download_zip_files_log)
    with open(csv_file_path, mode='r',encoding='utf-8') as csv_file:
                csv_reader = csv.reader(csv_file)
                for row in csv_reader:                                                   
                    if row[4] == "sent email" and row[1]:  # Assuming status is in the third column                     
                        row[4] = "downlaoded"  
                        row[7] = date.now().strftime("%Y-%m-%d %H:%M:%S")         
                    updated_rows.append(row) 

    with open(csv_file_path, mode='w', newline='',encoding='utf-8') as csv_file: 
        csv_writer = csv.writer(csv_file) 
        csv_writer.writerows(updated_rows)

def get_json_data(study_name):
    """
    Method to parse meta data json of a study and

    :param study_name:
    :return:
    """
    path = os.path.join(config.storage_folder , "studies/" , study_name)
    with open(path + '/' + study_name + '.json', encoding='utf-8') as fh:
        data = json.load(fh)

    #  if "enrolled-subjects" in data:
    #    data["number_of_enrolled_subjects"] = len(data["enrolled-subjects"])
    #  data["number_of_subjects"] = data["number_of_subjects"]
    #  data["number-of-subjects"] = data["number_of_subjects"]
    #  new_data = {}
    #  for key,value in data.items():
    #    key = key.replace("-","_")
    #    new_data[key] = value
    #  if "sensor_list" in data:
    #    new_data["sensor_size"] = len(data["sensor_list"]) * 2
    #  return new_data
    new_data = {}

    with open(path + '/' + study_name + '.json', encoding='utf-8') as fh:
        data = json.load(fh)

        # if "enrolled-subjects" in data:
        #    data["number_of_enrolled_subjects"] = len(data["enrolled-subjects"])
        data["number_of_subjects"] = data["number_of_subjects"]
        data["number-of-subjects"] = data["number_of_subjects"]

        for key, value in data.items():
            key = key.replace("-", "_")
            new_data[key] = value
        if "sensor_list" in data:
            new_data["sensor_size"] = len(data["sensor_list"]) * 2
            if "sensor_list_limited" in data:
                new_data["sensor_size"] = new_data["sensor_size"]  + ( len(data["sensor_list_limited"]) * 2)

    return new_data


def parse_get_dashboard_csv(study_name):
    df = read_study_df(study_name)
    # parsing the CSV in json format.
    json_records = df.reset_index().to_json(orient='records')
    data = json.loads(json_records)
    return data


def open_study_json(study_name):
    study_json_file_path = os.path.join(config.studies_folder, study_name, study_name + '.json')
    with open(study_json_file_path, 'r', encoding='utf-8') as f:
        study_json = json.load(f)
    return study_json


def update_study_df(study_name, id):
    study_df = read_study_df(study_name)
    for row in study_df.iterrows():
        if row[1].subject_name == id.split(':')[0] and row[1].app == id.split(':')[1]:
            study_df.loc[row[0], 'status_code'] = 3
    study_df.to_csv(os.path.join(config.storage_folder, config.csv_prefix + study_name + '.csv'), header=True,
                    index=False)


def read_study_df(study_name):
    study_csv = os.path.join(config.storage_folder, config.csv_prefix + study_name + '.csv')
    if os.path.isfile(study_csv):
        study_df = pd.read_csv(study_csv)
        return study_df
    else:
        return pd.DataFrame()


def get_user_list(study_df):
    return np.sort(
        np.unique(['_'.join(str(registration_id).split('_')[:-1]) for registration_id in study_df['subject_name']]))


def get_ids_and_app_list(users_per_app_dict):
    ids = []
    for app, ids_per_app in users_per_app_dict.items():
        ids.extend([id_per_app + constants.sep + app for id_per_app in ids_per_app])
    return sorted(ids)




def get_all_json_data(study_directories):
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """

    a_dict = {}
    for s_dir in study_directories:
        a_dict[dir] = get_json_data(s_dir)
    return a_dict


def save_study_json(study_id, study_json):
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """
    study_json_file_path = os.path.join(config.studies_folder, study_id, study_id + '.json')

    with open(study_json_file_path, 'w', encoding='utf-8') as jf:
        json.dump(study_json, jf, ensure_ascii=False, indent=4)

def create_backup_json_file(study_name, study_json):
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """
    if "version" not in study_json:
        study_json["version"] = 1
    concat_str = 'v'+str(study_json["version"])
    study_json[concat_str] = current_date
    backup_filename = study_name + '_' + concat_str + '_' + current_date +   '.json'
    backup_json_file_path = os.path.join(config.studies_folder, study_name, backup_filename)
    with open(backup_json_file_path, 'w', encoding='utf-8') as jf:
        json.dump(study_json, jf, ensure_ascii=False, indent=4)


def get_names(directory):
    """
    Method to get all files and folders in a directory
    Returns list of file names within directory
    
    :param directory: 
    :return: 
    """
    contents = os.listdir(directory)
    files, directories = [], []
    for item in contents:
        candidate = os.path.join(directory, item)
        if os.path.isdir(candidate):
            directories.append(item)
        else:
            files.append(item)
    return files, directories


def change_permissions(path):
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """
    # uid = pwd.getpwnam("www-data").pw_uid
    # gid = grp.getgrnam("jtrack").gr_gid
    os.chown(path, 33, 3619)
    #os.chown(path, 502, 20)
    os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)


def open_study_json(study_name):
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """
    study_json_file_path = os.path.join(config.studies_folder, study_name, study_name + '.json')
    with open(study_json_file_path, 'r', encoding='utf-8') as f:
        study_json = json.load(f)
    return study_json


def delete_user_files(study_name,subject_id):
    """
    Deletes all files associated with a user.

    :param user_id: The ID of the user whose files are to be deleted.
    """
    result = re.match(r'[A-Za-z_]+', subject_id)
    if result is not None:
        for index in range(1, 5):
            subject_str = subject_id + "_" + str(index)
            user_file = os.path.join(config.users_folder, study_name + "_" + subject_str + ".json")

            if os.path.exists(user_file):
                try:
                    os.remove(user_file)
                    logger.info("Deleted user file: %s", user_file)
                except Exception as e:
                    logger.error("Failed to delete user file %s: %s", user_file, str(e))


            user_folder = os.path.join(config.studies_folder, study_name, subject_str)
            if os.path.exists(user_folder):
                delete_local_subject_folder(user_folder)
            else:
                logger.info("User folder does not exist: %s", user_folder)

        juseless_folder_path = os.path.join(config.juseless_studies_folder, study_name,"inputs", subject_id)
        delete_remote_subject_folder(juseless_folder_path)


def delete_local_subject_folder(local_folder_path):
    """
    Deletes a folder locally and then deletes a folder on a remote server via SSH.
    """
    # Delete local folder
    if os.path.exists(local_folder_path) and os.path.isdir(local_folder_path):
        try:
            shutil.rmtree(local_folder_path)
            logger.info("Deleted local folder: %s", local_folder_path)
        except Exception as e:
            logger.error("Failed to delete local folder %s: %s", local_folder_path, str(e))
    else:
        logger.info("Local folder does not exist: %s", local_folder_path)

def delete_remote_subject_folder(juseless_folder_path):
    """
    Deletes a folder on a remote server via SSH.
    :param jusless_folder_path: Path to the folder on the remote server to be deleted.
    """
    # Construct and run remote SSH command
    ssh_command = (
        f"ssh {config.remote_username}@{config.juseless_server} "
        f"rm -Rf {juseless_folder_path}"
    )

    try:
        subprocess.run(ssh_command, shell=True, check=True)
        logger.info(" Deleted remote folder: %s", juseless_folder_path)
    except subprocess.CalledProcessError as e:
        logger.error("Remote deletion failed for %s: %s", juseless_folder_path, str(e))


import ast       
def to_list(val):
    """Coerce val into a list.
    - Lists pass through.
    - JSON / Python-literal strings are parsed.
    - Comma-separated strings are split.
    - Tuples/sets become lists.
    - None -> [] ; other scalars -> [val]
    """
    
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        lst = val.replace("'",'"')
        try:
            parsed = ast.literal_eval(lst)
            if isinstance(parsed, list):
                return parsed
        except Exception as e:
            pass        
    # Any other type -> wrap
    return val
