import json, os, csv,shutil,logging,re
import subprocess
import shlex
from datetime import datetime, date
from django.utils import timezone
import stat,subprocess
import numpy as np
import pandas as pd
from django.conf import settings
from jdash.config import runtime_config as config
from jdash.config import constants as constants
logger = logging.getLogger("django")
#create csv for loggin the downlaoded request
current_date = timezone.now().strftime('%Y%m%d%H%M%S')

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


def create_download_file_log(row):
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """
    csv_filepath = os.path.join(config.storage_folder,config.download_folder,config.download_zip_files_log)
    # Check if the file exists to decide on writing the header
    file_exists = os.path.isfile(csv_filepath)
    with open(csv_filepath, mode='a', newline='',encoding=constants.encoding) as file:
        writer = csv.writer(file)
        # If the file does not exist, write the header first
        if not file_exists:
            writer.writerow(['dataset','FirstName', 'Email', 'Link',  'Status','Requested','Emailed','Downloaded'])
        
        # Write the data row
        writer.writerow(row)


# updating the status of the downloaded status into csv file
def updated_status():
    """
    Update the CSV log file to mark studies with status 'sent email' as 'downloaded'
    and record the current timestamp.

    Reads and rewrites the file in-place.
    """
    updated_rows=[]
    csv_file_path = os.path.join(config.storage_folder,config.download_folder,config.download_zip_files_log)
    with open(csv_file_path, mode='r',encoding=constants.encoding) as csv_file:
                csv_reader = csv.reader(csv_file)
                for row in csv_reader:                                                   
                    if row[4] == "sent email" and row[1]:  # Assuming status is in the third column                     
                        row[4] = "downlaoded"  
                        row[7] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        print(f"status updated successfully for {row[0]}.")        
                    updated_rows.append(row) 

    with open(csv_file_path, mode='w', newline='',encoding=constants.encoding) as csv_file: 
        csv_writer = csv.writer(csv_file) 
        csv_writer.writerows(updated_rows)


def get_json_data(study_name):
    """
    Method to parse meta data json of a study and
    :param study_name:
    :return:
    """
    path = os.path.join(config.storage_folder , "studies/" , study_name)

    with open(path + '/' + study_name + '.json', encoding=constants.encoding) as fh:
        data = json.load(fh)

    # Set additional keys
    data["number_of_subjects"] = data.get("number_of_subjects", 0)
    data["number-of-subjects"] = data["number_of_subjects"]

    new_data = {}
    for key, value in data.items():
        new_key = key.replace("-", "_")
        new_data[new_key] = value

    if "sensor_list" in data:
        new_data["sensor_size"] = len(data["sensor_list"]) * 2
        if "sensor_list_limited" in data:
            new_data["sensor_size"] += len(data["sensor_list_limited"]) * 2

    return new_data

def handle_uploaded_file(f, name):
    """
    Method for handling file upload

    """
    with open(config.images_folder + name + constants.zip_extension, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
            
def parse_get_dashboard_csv(study_name):
    df = read_study_df(study_name)
    try:
        study_meta = get_json_data(study_name)
    except Exception:
        study_meta = {}
    df = merge_wearable_dashboard_data(df, study_name, study_meta.get("wearables", []))
    # parsing the CSV in json format.
    json_records = df.reset_index().to_json(orient='records')
    data = json.loads(json_records)
    return data



def build_wearable_dashboard_sensor_name(wearable_name, sensor_label):
    """
    Build the canonical dashboard sensor key for a wearable stream.

    Args:
        wearable_name (str): Device/manufacturer name, e.g. ``Garmin``.
        sensor_label (str): Wearable sensor label from study metadata.

    Returns:
        str: Normalized dashboard sensor name such as ``garmin_HEART_RATE``.
    """
    sensor_label = str(sensor_label or "").strip()
    sensor_label = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", sensor_label)
    sensor_label = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", sensor_label)
    sensor_label = re.sub(r"[^A-Za-z0-9]+", "_", sensor_label)
    sensor_label = re.sub(r"_+", "_", sensor_label).strip("_").upper()

    wearable_name = str(wearable_name or "").strip()
    wearable_name = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", wearable_name)
    wearable_name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", wearable_name)
    wearable_name = re.sub(r"[^A-Za-z0-9]+", "_", wearable_name)
    wearable_name = re.sub(r"_+", "_", wearable_name).strip("_").lower()

    if wearable_name and sensor_label:
        return f"{wearable_name}_{sensor_label}"
    return sensor_label


def merge_wearable_dashboard_data(base_df, study_name, wearables):
    """
    Merge wearable-specific dashboard CSV data into the main dashboard dataframe.

    Args:
        base_df (pd.DataFrame): Main dashboard dataframe.
        study_name (str): Study identifier.
        wearables (list): Wearable configuration list from study metadata.

    Returns:
        pd.DataFrame: Combined dataframe with wearable metrics included when present.
    """
    merged_df = base_df.copy()

    for wearable in wearables or []:
        wearable_df = pd.DataFrame()
        candidate_path = os.path.join(config.storage_folder, f"jtrack_wearables_{study_name}.csv")
        if os.path.isfile(candidate_path):
            try:
                wearable_df = pd.read_csv(candidate_path)
                print(wearable_df.columns)
            except Exception as exc:
                logger.warning(
                    "Failed to read wearable dashboard csv for study=%s path=%s error=%s",
                    study_name,
                    candidate_path,
                    exc,
                )

        if wearable_df.empty:
            continue

        if merged_df.empty:
            merged_df = wearable_df
            continue

        join_keys = [key for key in ("subject_name", "app") if key in merged_df.columns and key in wearable_df.columns]
        if not join_keys:
            logger.warning(
                "Skipping wearable dashboard merge for study=%s wearable=%s because no join keys were found.",
                study_name,
                wearable,
            )
            continue

        merged_df = merged_df.copy()
        merged_df["__row_order"] = range(len(merged_df))
        merged_indexed = merged_df.set_index(join_keys)
        wearable_indexed = wearable_df.drop_duplicates(subset=join_keys, keep="last").set_index(join_keys)
        merged_df = merged_indexed.combine_first(wearable_indexed).reset_index()
        if "__row_order" in merged_df.columns:
            merged_df = merged_df.sort_values("__row_order", na_position="last").drop(columns="__row_order")

    return merged_df

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
        a_dict[s_dir] = get_json_data(s_dir)
    return a_dict

def save_study_json(study_id, study_json):
    if not isinstance(study_json, dict):
        raise ValueError(f"Invalid study JSON for {study_id}: not a dict")

    required_keys = ["name", "survey"]
    missing = [key for key in required_keys if key not in study_json]

    if missing:
        raise ValueError(
            f"Refusing to overwrite {study_id}.json: missing keys {missing}. "
            f"Got keys: {list(study_json.keys())}"
        )

    study_json_file_path = os.path.join(
        config.studies_folder, study_id, study_id + '.json'
    )

    with open(study_json_file_path, 'w', encoding='utf-8') as jf:
        json.dump(study_json, jf, ensure_ascii=False, indent=4)

def create_backup_json_file(study_name, study_json):
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """
    # get number of json files 
    
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
    Set filesystem permissions for study folders.
    """
    try:
        os.chmod(
            path,
            stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH
        )
    except Exception:
        pass

import pwd,grp
def change_ownership(path):
    """
    Set filesystem ownership for study folders.
    """
    try:
        uid = pwd.getpwnam("www-data").pw_uid
        gid = grp.getgrnam("jtrack").gr_gid

        os.chown(path, uid, gid)

        for root, dirs, files in os.walk(path):
            for name in dirs:
                os.chown(os.path.join(root, name), uid, gid)
    except Exception:
        pass

def update_number_of_subjects(study_name, total_count):
    """
    Method for update_number_of_subjects

    """
    study_json = open_study_json(study_name)
    study_json[constants.key_name_number_of_subjects] = total_count
    save_study_json(study_name, study_json)

def open_study_json(study_name):
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """
    study_json_file_path = os.path.join(config.studies_folder, study_name, study_name + '.json')
    with open(study_json_file_path, 'r', encoding=constants.encoding) as f:
        study_json = json.load(f)
    return study_json

def delete_user_files(study_name,subject_id):
    """
    Deletes all files associated with a user.
    
    :param user_id: The ID of the user whose files are to be deleted.
    """
    
    result = re.match(r'[A-Za-z_]+', subject_id)
    if result is not None:
        for index in range(1, 4):
            subject_str = subject_id + "_" + str(index)
            user_file = os.path.join(config.users_folder, study_name + subject_str + ".json")
        
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
                
        juseless_folder_path = os.path.join(settings.JUSELESS_STUDIES_FOLDER, study_name,"inputs", subject_id)
        delete_remote_subject_folder(juseless_folder_path)
        

def delete_remote_subject_folder(jusless_folder_path):
    remote_target = shlex.quote(jusless_folder_path)

    ssh_runtime_dir = "/var/www/.ssh"
    known_hosts_path = os.path.join(ssh_runtime_dir, "known_hosts")
    ssh_key_path = getattr(
        settings,
        "ANALYTICS_PIPELINE_SSH_KEY",
        "/var/www/.ssh/id_ed25519_pipeline",
    )

    cmd = [
        "ssh",
        "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=no",
        "-o", f"UserKnownHostsFile={known_hosts_path}",
        "-o", "IdentitiesOnly=yes",
        "-i", ssh_key_path,
        f"{settings.REMOTE_USERNAME}@{settings.JUSELESS_SERVER}",
        f"rm -rf -- {remote_target}",
    ]
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Deleted remote folder: %s", jusless_folder_path)
        logger.debug("STDOUT: %s", result.stdout)
        logger.debug("STDERR: %s", result.stderr)

    except subprocess.CalledProcessError as e:
        logger.error("Remote deletion failed for %s", jusless_folder_path)
        logger.error("Return code: %s", e.returncode)
        logger.error("STDOUT: %s", e.stdout)
        logger.error("STDERR: %s", e.stderr)

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


import shlex 
import ast       
def to_list(val):
    """Coerce val into a list.
    - Lists pass through.
    - JSON / Python-literal strings are parsed.
    - Comma-separated strings are split.
    - Tuples/sets become lists.
    - None -> [] ; other scalars -> [val]
    """
    if val in [None,""]:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        lst = val.replace("'",'"')
        try:
            parsed = ast.literal_eval(lst)
            print(f"to_list parsed: {parsed} ({type(parsed)})")
            if isinstance(parsed, list):
                return parsed
        except Exception as e:
            pass        
    # Any other type -> wrap
    return [val]
