import copy
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


def build_wearable_dashboard_csv_candidates(study_name):
    """
    Build candidate wearable-dashboard CSV paths for a study.

    Args:
        study_name (str): Study identifier.

    Returns:
        list[str]: Candidate CSV paths to inspect.
    """
    return [
        os.path.join(config.storage_folder, f"jtrack_wearables_{study_name}.csv"),
        os.path.join(config.storage_folder, f"jtrack_wearable_{study_name}.csv"),
    ]


def normalize_wearable_dashboard_columns(wearable_df, wearable):
    """
    Normalize wearable CSV column names into the dashboard column convention
    expected by the details-table logic, e.g. ``garmin_HEART_RATE n_batches``.

    Args:
        wearable_df (pd.DataFrame): Raw wearable dataframe.
        wearable (dict): Wearable configuration block from study metadata.

    Returns:
        pd.DataFrame: Dataframe with renamed wearable metric columns where
        a confident mapping was possible.
    """
    if wearable_df.empty:
        return wearable_df

    wearable_name = str((wearable or {}).get("sensorname") or "").strip()
    configured_sensors = []
    for sensor in (wearable or {}).get("sensors", []):
        label = str((sensor or {}).get("wearable_sensor", "")).strip()
        if not label:
            continue
        configured_sensors.append(
            (
                label,
                build_wearable_dashboard_sensor_name(wearable_name, label),
            )
        )

    if not configured_sensors:
        return wearable_df

    def _normalize_token(value):
        return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())

    def _strip_numeric_suffix(value):
        return re.sub(r"\d+$", "", value or "")

    wearable_name_token = _normalize_token(wearable_name)
    candidate_map = {}
    for label, dashboard_sensor_name in configured_sensors:
        names = {
            label,
            label.replace(" ", "_"),
            label.replace(" ", ""),
            dashboard_sensor_name,
        }
        for candidate in names:
            candidate_map[_normalize_token(candidate)] = dashboard_sensor_name

    renames = {}
    for column in wearable_df.columns:
        if column in {"subject_name", "app"}:
            continue

        metric_suffix = None
        sensor_token = None
        for suffix in (" last_time_received", "_last_time_received"):
            if column.endswith(suffix):
                metric_suffix = " last_time_received"
                sensor_token = column[: -len(suffix)]
                break

        if metric_suffix is None:
            for suffix in (" n_batches", "_n_batches"):
                if column.endswith(suffix):
                    metric_suffix = " n_batches"
                    sensor_token = column[: -len(suffix)]
                    break

        if metric_suffix is None or sensor_token is None:
            continue

        normalized_sensor_token = _normalize_token(sensor_token)
        sensor_variants = {
            normalized_sensor_token,
            _strip_numeric_suffix(normalized_sensor_token),
        }
        if wearable_name_token and normalized_sensor_token.startswith(wearable_name_token):
            without_prefix = normalized_sensor_token[len(wearable_name_token):]
            sensor_variants.add(without_prefix)
            sensor_variants.add(_strip_numeric_suffix(without_prefix))

        matched_sensor_name = None
        for variant in sensor_variants:
            if variant and variant in candidate_map:
                matched_sensor_name = candidate_map[variant]
                break

        if matched_sensor_name:
            renames[column] = f"{matched_sensor_name}{metric_suffix}"

    if renames:
        wearable_df = wearable_df.rename(columns=renames)

    return wearable_df


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
        for candidate_path in build_wearable_dashboard_csv_candidates(study_name):
            if os.path.isfile(candidate_path):
                try:
                    wearable_df = pd.read_csv(candidate_path)
                except Exception as exc:
                    logger.warning(
                        "Failed to read wearable dashboard csv for study=%s path=%s error=%s",
                        study_name,
                        candidate_path,
                        exc,
                    )
                else:
                    wearable_df = normalize_wearable_dashboard_columns(wearable_df, wearable)
                    break

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

    required_keys = [constants.key_study_name_json, constants.key_name_survey]
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


def _next_study_json_version(study_json):
    try:
        return int(study_json.get(constants.key_name_version, 1)) + 1
    except (TypeError, ValueError):
        return 2


def save_study_json_with_version_backup(study_name, study_json):
    create_backup_json_file(study_name, copy.deepcopy(study_json))
    study_json[constants.key_name_version] = _next_study_json_version(study_json)
    save_study_json(study_name, study_json)


def create_backup_json_file(study_name, study_json):
    """
    Method to parse meta data json of  all studies
    
    :param study_directories: 
    :return: 
    """
    # get number of json files 
    
    if constants.key_name_version not in study_json:
        study_json[constants.key_name_version] = 1
    concat_str = 'v'+str(study_json[constants.key_name_version])
    current_date = timezone.now().strftime('%Y%m%d%H%M%S')
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
            for name in files:
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

#methods related to old survey editing and updating

def _legacy_survey_questions(study_json):
    survey = study_json.setdefault(constants.key_name_survey, {})
    questions = survey.setdefault(constants.key_name_questions, [])
    if not isinstance(questions, list):
        raise ValueError("Study survey questions must be a list.")
    return questions


def _legacy_question_id(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _legacy_bool_int(value, default=0):
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)):
        return 1 if value else 0
    return 1 if str(value).strip().lower() in ("1", "true", "yes", "y", "on") else 0


def _normalize_legacy_question_flags(question):
    if constants.field_name_active in question:
        question[constants.field_name_active] = 1
    if constants.field_name_mandatory in question:
        question[constants.field_name_mandatory] = 0
    return question


def _remap_legacy_question_refs(value, id_map):
    if value in (None, "", [], {}):
        return value

    question_ids = _legacy_question_ids_from_value(value)
    if not question_ids:
        return value

    remapped_ids = [id_map.get(question_id, question_id) for question_id in question_ids]
    if isinstance(value, tuple):
        return tuple(remapped_ids)
    if isinstance(value, set):
        return set(remapped_ids)
    if isinstance(value, str):
        raw_value = value.strip()
        if raw_value.startswith("["):
            return json.dumps(remapped_ids)
        if ";" in raw_value:
            return ";".join(str(question_id) for question_id in remapped_ids)
        if "," in raw_value:
            return ",".join(str(question_id) for question_id in remapped_ids)
        return str(remapped_ids[0]) if len(remapped_ids) == 1 else ",".join(
            str(question_id) for question_id in remapped_ids
        )
    return remapped_ids


def _find_legacy_question_index(questions, question_id=None, title=None):
    normalized_id = _legacy_question_id(question_id)
    if normalized_id is not None:
        for index, question in enumerate(questions):
            if _legacy_question_id(question.get(constants.key_name_id)) == normalized_id:
                return index

    if title:
        for index, question in enumerate(questions):
            if question.get(constants.field_name_title) == title:
                return index

    raise ValueError("Question was not found in the study survey file.")


def _next_legacy_question_id(questions):
    existing_ids = [
        _legacy_question_id(question.get(constants.key_name_id))
        for question in questions
    ]
    existing_ids = [question_id for question_id in existing_ids if question_id is not None]
    return max(existing_ids, default=0) + 1


def _split_legacy_choice_text(value):
    return [
        choice.strip()
        for choice in str(value or "").split(";")
        if choice.strip()
    ]


def _legacy_question_ids_from_value(value):
    if value in (None, "", [], {}):
        return []
    if isinstance(value, (list, tuple, set)):
        return [
            question_id
            for question_id in (_legacy_question_id(item) for item in value)
            if question_id is not None
        ]
    if isinstance(value, int):
        return [value]

    raw_value = str(value).strip()
    if not raw_value or raw_value.lower() in ("[]", "none", "null"):
        return []

    try:
        parsed_value = json.loads(raw_value.replace("'", '"'))
        if isinstance(parsed_value, list):
            return _legacy_question_ids_from_value(parsed_value)
    except (TypeError, ValueError):
        pass

    return [
        question_id
        for question_id in (
            _legacy_question_id(item.strip().strip('"').strip("'"))
            for item in re.split(r"[,;]", raw_value.strip("[]"))
        )
        if question_id is not None
    ]


def _normalize_legacy_answer_keys(answer):
    if not isinstance(answer, dict):
        return answer

    if constants.field_name_minVal not in answer and constants.field_name_minValue in answer:
        answer[constants.field_name_minVal] = answer[constants.field_name_minValue]
    if constants.field_name_maxVal not in answer and constants.field_name_maxValue in answer:
        answer[constants.field_name_maxVal] = answer[constants.field_name_maxValue]
    answer.pop(constants.field_name_minValue, None)
    answer.pop(constants.field_name_maxValue, None)
    return answer


def _build_legacy_answers(question_type, answer_data, existing_answers=None):
    existing_answers = list(existing_answers or [])
    answer_data = answer_data or {}
    question_type = _legacy_question_id(question_type)

    if question_type in (1, 2):
        choices = _split_legacy_choice_text(answer_data.get(constants.field_name_text))
        if not choices:
            return existing_answers

        answers = []
        for index, choice in enumerate(choices):
            answer = copy.deepcopy(existing_answers[index]) if index < len(existing_answers) else {}
            answer[constants.key_name_id] = answer.get(constants.key_name_id, index + 1)
            answer[constants.field_name_text] = choice
            answer.setdefault(constants.field_name_value, index + 1)
            answers.append(_normalize_legacy_answer_keys(answer))
        return answers

    answer = copy.deepcopy(existing_answers[0]) if existing_answers else {}
    answer[constants.key_name_id] = answer.get(constants.key_name_id, 1)
    answer[constants.field_name_text] = (
        answer_data.get(constants.field_name_text)
        or answer.get(constants.field_name_text, "N")
    )
    for key in (
        constants.field_name_answerSubText,
        constants.field_name_value,
        constants.field_name_defaultValue,
        constants.field_name_stepSize,
        constants.field_name_minText,
        constants.field_name_maxText,
        constants.field_name_answerSortId,
    ):
        value = answer_data.get(key)
        if value not in (None, ""):
            answer[key] = value
    min_value = answer_data.get(
        constants.field_name_minVal,
        answer_data.get(constants.field_name_minValue),
    )
    if min_value not in (None, ""):
        answer[constants.field_name_minVal] = min_value
    max_value = answer_data.get(
        constants.field_name_maxVal,
        answer_data.get(constants.field_name_maxValue),
    )
    if max_value not in (None, ""):
        answer[constants.field_name_maxVal] = max_value
    _normalize_legacy_answer_keys(answer)
    return [answer]


def update_legacy_survey_question(study_name, question_data, answer_data=None):
    study_json = open_study_json(study_name)
    questions = _legacy_survey_questions(study_json)
    question_index = _find_legacy_question_index(
        questions,
        question_id=question_data.get(constants.key_name_id),
    )
    question = questions[question_index]

    for key, value in question_data.items():
        if key == constants.key_name_id:
            continue
        if key == constants.field_name_active:
            question[key] = 1
            continue
        if key == constants.field_name_mandatory:
            question[key] = 0
            continue
        if value is not None:
            question[key] = value

    question[constants.key_name_id] = (
        _legacy_question_id(question_data.get(constants.key_name_id))
        or question.get(constants.key_name_id)
    )
    question[constants.field_name_answer] = _build_legacy_answers(
        question.get(constants.field_name_questionType),
        answer_data,
        question.get(constants.field_name_answer, []),
    )
    _normalize_legacy_question_flags(question)

    save_study_json_with_version_backup(study_name, study_json)
    return study_json


def update_legacy_survey_question_order(study_name, question_id, new_sort_id):
    study_json = open_study_json(study_name)
    questions = _legacy_survey_questions(study_json)
    new_sort_id = _legacy_question_id(new_sort_id)

    if not questions:
        return study_json
    if new_sort_id is None or new_sort_id < 1 or new_sort_id > len(questions):
        raise ValueError(f"Question order must be between 1 and {len(questions)}.")

    current_index = _find_legacy_question_index(questions, question_id=question_id)
    question = questions.pop(current_index)
    questions.insert(new_sort_id - 1, question)

    ordered_questions = [
        (question, _legacy_question_id(question.get(constants.key_name_id)) or index)
        for index, question in enumerate(questions, start=1)
    ]
    id_map = {
        old_id: index
        for index, (question, old_id) in enumerate(ordered_questions, start=1)
    }

    for index, (question, old_id) in enumerate(ordered_questions, start=1):
        question[constants.key_name_id] = index
        for field_name in (constants.field_name_activate_question, constants.field_name_deactivate_question):
            if field_name in question:
                question[field_name] = _remap_legacy_question_refs(
                    question.get(field_name),
                    id_map,
                )
        _normalize_legacy_question_flags(question)

    save_study_json_with_version_backup(study_name, study_json)
    return study_json


def delete_legacy_survey_question(study_name, question_id=None, title=None):
    return delete_legacy_survey_questions(study_name, question_ids=[question_id], title=title)


def delete_legacy_survey_questions(study_name, question_ids=None, title=None):
    study_json = open_study_json(study_name)
    questions = _legacy_survey_questions(study_json)

    selected_ids = {
        question_id
        for question_id in (_legacy_question_id(value) for value in (question_ids or []))
        if question_id is not None
    }

    if not selected_ids and title:
        selected_ids.add(
            _legacy_question_id(
                questions[_find_legacy_question_index(questions, title=title)].get(constants.key_name_id)
            )
        )

    if not selected_ids:
        return study_json

    linked_questions = []
    for question in questions:
        current_id = _legacy_question_id(question.get(constants.key_name_id))
        if current_id in selected_ids:
            continue

        linked_ids = set(_legacy_question_ids_from_value(question.get(constants.field_name_activate_question)))
        linked_ids.update(_legacy_question_ids_from_value(question.get(constants.field_name_deactivate_question)))
        if linked_ids.intersection(selected_ids):
            linked_questions.append(current_id)

    if linked_questions:
        raise ValueError(
            "Cannot delete selected question(s) because they are used in "
            f"activation/deactivation conditions by question(s): {', '.join(map(str, linked_questions))}."
        )

    questions[:] = [
        question
        for question in questions
        if _legacy_question_id(question.get(constants.key_name_id)) not in selected_ids
    ]
    save_study_json_with_version_backup(study_name, study_json)
    return study_json


def update_legacy_survey_categories(study_name, category_list, collect_flag=False):
    study_json = open_study_json(study_name)
    survey = study_json.setdefault(constants.key_name_survey, {})
    questions = _legacy_survey_questions(study_json)
    existing_categories = survey.get(constants.key_name_categories, []) or []
    existing_values = {
        _legacy_question_id(category.get(constants.key_name_categoryValue))
        for category in existing_categories
        if isinstance(category, dict)
    }
    existing_values.discard(None)

    updated_categories = []
    for index, category in enumerate(category_list or [], start=1):
        title = str(category.get(constants.key_name_categoryTitle, "")).strip()
        if not title:
            continue

        category_value = _legacy_question_id(category.get(constants.key_name_categoryValue)) or index
        updated_categories.append(
            {
                constants.key_name_categoryTitle: title,
                constants.key_name_categoryValue: category_value,
                constants.key_name_didSubjectAsk: bool(collect_flag),
            }
        )

    updated_values = {
        _legacy_question_id(category.get(constants.key_name_categoryValue))
        for category in updated_categories
    }
    updated_values.discard(None)
    deleted_values = existing_values - updated_values

    if deleted_values:
        for question in questions:
            if _legacy_question_id(question.get(constants.field_name_category)) in deleted_values:
                question[constants.field_name_category] = 0

    survey[constants.key_name_categories] = updated_categories
    save_study_json_with_version_backup(study_name, study_json)
    return study_json


def duplicate_legacy_survey_question(study_name, question_id):
    study_json = open_study_json(study_name)
    questions = _legacy_survey_questions(study_json)
    question_index = _find_legacy_question_index(questions, question_id=question_id)
    duplicated_question = copy.deepcopy(questions[question_index])
    duplicated_question.pop(constants.field_name_db_id, None)
    duplicated_question[constants.key_name_id] = _next_legacy_question_id(questions)
    _normalize_legacy_question_flags(duplicated_question)
    for answer in duplicated_question.get(constants.field_name_answer, []):
        if isinstance(answer, dict):
            answer.pop(constants.field_name_db_id, None)
            _normalize_legacy_answer_keys(answer)
    questions.append(duplicated_question)
    save_study_json_with_version_backup(study_name, study_json)
    return study_json


def delete_legacy_survey(study_name):
    study_json = open_study_json(study_name)
    study_json[constants.key_name_survey] = {}
    save_study_json_with_version_backup(study_name, study_json)
    return study_json


