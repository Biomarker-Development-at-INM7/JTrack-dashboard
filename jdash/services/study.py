###########################################################################
####           study.py
####           this file contains all the service methods related to studies
####           initial version written by mstolz
####           reproduced/modified by mnarava
####            Refactored and extended for clarity and robustness.
####
###########################################################################

import base64
import glob
import json
import logging
import os
import re
import subprocess
import threading
import zipfile
from datetime import datetime
from django.utils import timezone
import numpy as np
import pandas as pd
from django.conf import settings
from django.contrib.auth.models import Group
from django.db import connection
from pandas.errors import EmptyDataError
from jdash.config import constants as constants
from jdash.config import runtime_config as config
import jdash.exceptions.studyexceptions as studyexceptions
from jdash.utils.utils import (
        build_quality_control_test_cases,
    calculate_stats_of_number_of_subjects,
    create_sql_statements_for_quality_control_tests,
    get_latest_received_study_sensor_details,
)
from jdash.utils.fileutils import (
        build_wearable_dashboard_sensor_name,
    get_json_data,
    change_permissions,
    save_study_json,
    open_study_json,
    read_study_df,
    get_user_list,
    get_ids_and_app_list,
    get_all_json_data,
    parse_get_dashboard_csv,
    create_backup_json_file,
    change_ownership,
)
from jdash.services.datahelper import validate_empty
from jdash.services.subject import Subject
from jdash.services.survey import Survey
from jdash.repositories.study_repository import (
    create_new_study_in_db,
    close_study_model,
    retrieve_all_studies_for_user,
    retrieve_study_details_by_title,
    update_study_db_details,
)
from jdash.repositories.survey_repository import create_survey_in_db, retrieve_survey
from jdash.models import QualityControlTests as qctestsModel
logger = logging.getLogger("django")
# Get the current date in the desired format
current_date = timezone.now().strftime('%Y-%m-%d')

def _get_study_group_members(study_name, user=None):
    """
    Resolve investigator and viewer usernames for a study group.

    Args:
        study_name (str): Name of the study whose group members are requested.
        user (User, optional): Current user to exclude from the returned lists.

    Returns:
        tuple: Two lists containing investigator usernames and viewer usernames.
    """
    investigators = []
    viewers = []
    group_name = f"{study_name}_group"

    try:
        study_group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return investigators, viewers

    for member in study_group.user_set.all().order_by("username"):
        if user is not None and member.pk == user.pk:
            continue
        member_group_names = set(member.groups.values_list("name", flat=True))
        if "administrator" in member_group_names:
            continue
        if constants.group_name_investigator in member_group_names:
            investigators.append(member.username)
        elif constants.group_name_viewer in member_group_names:
            viewers.append(member.username)
        else:
            viewers.append(member.username)

    return investigators, viewers


class Study:
    """Class representing a Study"""
    def __init__(self, study_name: str, user):
        """
        Initialize the study service for a specific study and user.

        Args:
            study_name (str): Name of the study.
            user (User): User operating on the study.
        """
        self.study_name = study_name
        self.user = user
        self._meta = None
        self._survey = None
        self._loaded = False
        
        # ── Properties ──────────────────────────────────────────────────────────────

    @property
    def path(self) -> str:
        """Filesystem root for this study."""
        return os.path.join(config.studies_folder, self.study_name)

    @property
    def bids_path(self) -> str:
        """BIDS‐analysis folder for this study."""
        return os.path.join(config.analytics_storage_folder, self.study_name)

    @property
    def dash_root(self) -> str:
        """Dashboard subfolder (for QR & sheets)."""
        return os.path.join(settings.DASH_FOLDER, config.app_study_folder, self.study_name)

    @property
    def meta(self) -> dict:
        """Lazily load & cache the study’s JSON metadata."""
        if not self._loaded:
            self._meta = get_json_data(self.study_name)
            self._loaded = True
        return self._meta

    @meta.setter
    def meta(self, new_meta: dict):
        """Overwrite the in‐memory metadata & persist."""
        self._meta = new_meta
        self._loaded = True

    @property
    def created_at(self) -> datetime:
        """When this instance was first created (in memory)."""
        return datetime.now().astimezone()

    @property
    def number_of_subjects(self) -> int:
        """
        Return the configured number of subjects from study metadata.

        Returns:
            int: Number of subjects stored in the study metadata.
        """
        return self.meta.get(constants.key_name_number_of_subjects, 0)

    @number_of_subjects.setter
    def number_of_subjects(self, new_count: int):
        """
        Update the in-memory subject count.

        Args:
            new_count (int): New number of subjects.
        """
        self.meta[constants.key_name_number_of_subjects] = new_count

    @property
    def survey(self):
        """Retrieve or create the Survey object and JSON."""
        self.meta.setdefault(constants.field_name_survey, {})
        if self._survey is None:
            raw = self.meta[constants.field_name_survey]
            if not raw:
                return None
            if isinstance(raw, int):
                self._survey = retrieve_survey(raw)
            else:
                self._survey = create_survey_in_db(self.study_name, raw, self.user)
            # store the JSON back into meta
            self.meta[constants.field_name_survey] = json.dumps(
                Survey.generate_json_for_study(self._survey.id)
            )
        return self._survey

    @property
    def sensors(self) -> list:
        """List of sensor names that have 'n_batches' in the CSV headers."""
        return [
            col.split(' ')[0]
            for col in self.meta.get(constants.key_name_sensor_list, [])
            if 'n_batches' in col
        ]
        
        
    # ── Core Methods ────────────────────────────────────────────────────────────

    def persist_meta(self):
        """Save the in‐memory metadata back to disk."""
        save_study_json(self.study_name, self.meta)

    def create(self) -> bool:
        """
        High‐level: make directories, save JSON, create DB row,
        fire off background PDFs & test cases.
        """
        logger.info("Study.create called for study_name=%s user=%s", self.study_name, self.user)
        if not os.path.isdir(self.path):
            self._make_directories()
        images_url = self._store_images()
        self.meta.setdefault(constants.field_name_survey, {})
        if self.survey:
            # survey property setter already updated self.meta
            pass  
        self.persist_meta()
        create_new_study_in_db(self.user, self.meta, self._survey, images_url)
        self._start_subjects_pdf()
        self._create_test_cases()
        logger.info("Study.create finished for study_name=%s", self.study_name)
        logger.debug("Study.create return_value=%s", True)
        return True

    def _make_directories(self):
        """
        Create the required filesystem directories for the study.
        """

        os.makedirs(self.path, exist_ok=True)
        change_permissions(self.path)

        os.makedirs(
            os.path.join(self.bids_path, config.analytics_outputs_folder),
            exist_ok=True
        )
        change_permissions(self.bids_path)
        change_ownership(self.bids_path);
        os.makedirs(self.dash_root, exist_ok=True)
        change_permissions(self.dash_root)

        for sub in (config.qr_folder, config.sheets_folder):
            sub_path = os.path.join(self.dash_root, sub)
            os.makedirs(sub_path, exist_ok=True)
            change_permissions(sub_path)

    def _store_images(self) -> str:
        """
        Decode and persist uploaded study images when present.

        Returns:
            str: Images folder marker when images are stored, otherwise an empty string.
        """
        key = constants.field_name_images
        if key in self.meta and self.meta[key]:
            data = base64.b64decode(self.meta[key])
            out = os.path.join(self.path, f"{self.study_name}_images.zip")
            with open(out, 'wb') as f: f.write(data)
            self.meta[key] = True
            return constants.images_folder
        self.meta[key] = False
        return ""

    def _start_subjects_pdf(self):
        """
        Start background generation of subject PDF/QR artifacts.

        Returns:
            None
        """
        t = threading.Thread(
            target=Subject.create_pdfs_for_study,
            args=(self.study_name, self.number_of_subjects),
            daemon=True,
        )
        t.start()

    def _create_test_cases(self):
        """
        Generate and execute default quality-control test cases for the study.

        Returns:
            None
        """
        stmt_file = os.path.join(self.path, f"{self.study_name}_test_cases.sql")
        study_id = json.loads(retrieve_study_details_by_title(self.study_name))[constants.key_name_id]
        create_sql_statements_for_quality_control_tests(self.meta, stmt_file, study_id)
        with open(stmt_file, encoding=constants.encoding) as f:
            stmts = [s.strip() for s in f.read().split(';') if s.strip()]
        with connection.cursor() as cur:
            for s in stmts: cur.execute(s)

    def display_context(self) -> dict:
        """
        Return the exact context dict your template expects.
        """
        logger.info("Study.display_context called for study_name=%s", self.study_name)
        ctx = {'meta_data': self.meta}
        self._ensure_legacy_survey_ids(ctx["meta_data"])
        dashboard_sensors = self._get_dashboard_sensor_names(ctx["meta_data"])
        ctx["meta_data"]["dashboard_sensor_list"] = dashboard_sensors
        ctx["meta_data"]["sensor_size"] = len(dashboard_sensors) * 2
        raw = parse_get_dashboard_csv(self.study_name)
        # ensure all sensors appear
        for sensor in dashboard_sensors:
            for row in raw:
                row.setdefault(f"{sensor} n_batches", 0)
                row.setdefault(f"{sensor} last_time_received", "none")
        grouping, count = self._group_by_subject(raw)
        ctx['meta_data'][constants.key_name_number_of_subjects] = count
        ctx['d'] = json.loads(grouping)
        ctx['subject_details'] = self._collect_subject_details(raw)
        logger.info("Study.display_context finished for study_name=%s", self.study_name)
        logger.debug("Study.display_context return_value=%s", ctx)
        return ctx
    
    @staticmethod
    def _get_dashboard_sensor_names(meta_data):
        """
        Build the sensor list used by the live-monitoring table.

        This includes passive sensors, active sensors, and wearable sensors so
        dashboard rows can surface Garmin/wearable metrics when those columns
        exist in the CSV.
        """
        ordered = []

        def _add(sensor_name):
            sensor_name = str(sensor_name or "").strip()
            if sensor_name and sensor_name not in ordered:
                ordered.append(sensor_name)

        for sensor_name in meta_data.get(constants.key_name_sensor_list, []) or []:
            _add(sensor_name)

        for sensor_name in meta_data.get("sensor_list_limited", []) or []:
            _add(sensor_name)

        for wearable in meta_data.get("wearables", []) or []:
            if not isinstance(wearable, dict):
                continue
            wearable_name = wearable.get("sensorname", "")
            for sensor in wearable.get("sensors", []) or []:
                if not isinstance(sensor, dict):
                    continue
                _add(
                    build_wearable_dashboard_sensor_name(
                        wearable_name,
                        sensor.get("wearable_sensor", ""),
                    )
                )
        return ordered

    @staticmethod
    def _ensure_legacy_survey_ids(meta_data: dict):
        """
        Inject the legacy survey id marker for file-backed EMA studies.

        Args:
            meta_data (dict): Study metadata dictionary to normalize.

        Returns:
            None
        """
        survey_data = meta_data.get("survey")
        if isinstance(survey_data, dict) and "id" not in survey_data:
            if "survey_ios" in meta_data:
                meta_data["survey_ios"]["id"] = "999"
            meta_data["survey"]["id"] = "999"

    def _group_by_subject(self, data):
        """
        Group parsed dashboard rows by logical subject id.

        Args:
            data (list): Parsed dashboard CSV rows.

        Returns:
            tuple: JSON string of grouped rows and grouped subject count.
        """
        grouped = {}
        for obj in data:
            g = obj['subject_name'][:-2]
            grouped.setdefault(g, []).append(obj)
        return json.dumps(grouped, sort_keys=True), len(grouped)

    def _collect_subject_details(self, data):
        """
        Build subject-removal details from parsed dashboard data.

        Args:
            data (list): Parsed dashboard CSV rows.

        Returns:
            dict: Subject detail payload used by the details page.
        """
        details = []
        for obj in data:
            ds =  Subject.load_details(self.study_name, obj['subject_name'])
            sub = Subject(obj, ds)
            if sub.status == 0:
                details.append(
                    f"{sub.subject_name}{constants.sep}{sub.app}"
                    f"{constants.value_sep}{sub.date_left_study != 'none'}"
                )
        return {'ids_to_be_removed': sorted(details)}

    def update_details(self, values_obj):
        """
        Update the study metadata JSON with submitted study edit values.

        Args:
            values_obj (dict): Normalized study update payload.

        Returns:
            dict: Updated study JSON payload.
        """
        logger.info(
            "Study.update_details called for study_name=%s keys=%s",
            self.study_name,
            list(values_obj.keys()),
        )
        study_json = open_study_json(self.study_name)

        create_backup_json_file(self.study_name, study_json)

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
            if len(values_obj['task_list']) == 0 and len(values_obj['sensor_list_limited']) == 0:
                study_json[constants.field_name_labeling] = 0

            if len(values_obj['task_list']) > 0 and len(values_obj['sensor_list_limited']) > 0:
                study_json[constants.field_name_labeling] = 1

            if len(values_obj['sensor_list']) > 0 and len(values_obj['task_list']) > 0:
                study_json[constants.field_name_labeling] = 2

            if len(values_obj['sensor_list']) > 0 and len(values_obj['sensor_list_limited']) > 0:
                study_json[constants.field_name_labeling] = 3

        if 'survey' in values_obj:
            logger.info("update_study_details:: survey %s", values_obj['survey'])
            if type(values_obj['survey']) == int:
                study_json['survey'] = Survey.generate_json_for_download(values_obj['survey'])
            else:
                study_json['survey'] = values_obj['survey']
        
        if 'wearables' in values_obj:
            study_json['wearables'] = values_obj['wearables']

        if 'device_sensor_rows' in values_obj:
            study_json['device_sensor_rows'] = values_obj['device_sensor_rows']
        
        # Keep the study JSON schema stable even when EMA is disabled or omitted
        # from the submitted update payload. Some deployed save guards require the
        # survey key to exist on every overwrite.
        if constants.field_name_survey not in study_json or study_json[constants.field_name_survey] is None:
            study_json[constants.field_name_survey] = {}

        study_json["version"] = study_json["version"] + 1
        save_study_json(self.study_name, study_json)
        self.meta = study_json
        logger.info("Study.update_details finished for study_name=%s", self.study_name)
        logger.debug("Study.update_details return_value=%s", study_json)
        return study_json

    def update(self, values_obj):
        """
        Run the full study update workflow.

        This method updates the study JSON metadata, synchronizes database
        state, and triggers the post-update JSON refresh script.

        Args:
            values_obj (dict): Normalized study update payload.

        Returns:
            dict: Updated study JSON payload.
        """
        logger.info("Study.update called for study_name=%s", self.study_name)
        study_json = self.update_details(values_obj)
        update_study_db_details(values_obj)
        self._refresh_test_cases()
        self._trigger_update_json_script()
        logger.info("Study.update finished for study_name=%s", self.study_name)
        logger.debug("Study.update return_value=%s", study_json)
        return study_json

    def _refresh_test_cases(self):
        """
        Sync quality-control test cases after a study update.

        Returns:
            None
        """
        study_id = json.loads(retrieve_study_details_by_title(self.study_name))[constants.key_name_id]
        desired_cases = build_quality_control_test_cases(self.meta)
        existing_cases = list(qctestsModel.objects.filter(study_id=study_id))

        def _semantic_key_from_existing(test_case):
            testcase_id = str(test_case.testcase_id or "")
            if testcase_id.startswith(("DATA-", "SUB-")):
                return testcase_id

            if testcase_id.startswith("EMA-"):
                return f"EMA|{testcase_id.removeprefix('EMA-')}"

            if testcase_id.startswith("PSEN-"):
                match = re.search(
                    r"for (?P<sensor>.+?) on (?P<platform>Android|iOS)$",
                    str(test_case.description or ""),
                )
                if match:
                    return f"PSEN|{match.group('platform')}|{match.group('sensor')}"

            if testcase_id.startswith("ASEN-"):
                match = re.search(
                    r"1\. Simulate (?P<sensor>.+?) for a subject",
                    str(test_case.steps or ""),
                )
                if match:
                    return f"ASEN|{match.group('sensor')}"

            if testcase_id.startswith("WDEV-"):
                match = re.search(
                    r"Verify (?P<device>.+?) wearable data is logged correctly for (?P<sensor>.+?) on (?P<platform>Android|iOS)$",
                    str(test_case.description or ""),
                )
                if match:
                    return (
                        f"WDEV|{match.group('platform')}|"
                        f"{match.group('device')}|{match.group('sensor')}"
                    )

            return testcase_id

        existing_by_key = {
            _semantic_key_from_existing(test_case): test_case
            for test_case in existing_cases
        }

        matched_existing_by_key = {}
        used_existing_ids = set()
        for case in desired_cases:
            existing = existing_by_key.get(case["semantic_key"])
            if existing is not None and existing.id in used_existing_ids:
                existing = None

            if existing is None and case["semantic_key"].startswith("EMA|"):
                existing = next(
                    (
                        test_case
                        for test_case in existing_cases
                        if test_case.id not in used_existing_ids
                        and str(test_case.testcase_id or "").startswith("EMA-")
                        and str(test_case.description or "") == case["description"]
                    ),
                    None,
                )

            if existing is None:
                legacy_key = case.get("legacy_semantic_key")
                legacy_existing = existing_by_key.get(legacy_key)
                if legacy_existing is not None and legacy_existing.id not in used_existing_ids:
                    existing = legacy_existing

            if existing is not None:
                matched_existing_by_key[case["semantic_key"]] = existing
                used_existing_ids.add(existing.id)

        stale_cases = [
            test_case
            for test_case in existing_cases
            if test_case.id not in used_existing_ids
        ]
        if stale_cases:
            qctestsModel.objects.filter(id__in=[test_case.id for test_case in stale_cases]).delete()

        rows_to_rekey = []
        for case in desired_cases:
            existing = matched_existing_by_key.get(case["semantic_key"])
            if existing and existing.testcase_id != case["testcase_id"]:
                existing.testcase_id = f"TMP-{existing.id}"
                rows_to_rekey.append(existing)

        if rows_to_rekey:
            qctestsModel.objects.bulk_update(rows_to_rekey, ["testcase_id"])

        for case in desired_cases:
            existing = matched_existing_by_key.get(case["semantic_key"])
            if existing:
                changed_fields = []
                for field in ("testcase_id", "test_type", "description", "steps", "expected_outcome"):
                    if getattr(existing, field) != case[field]:
                        setattr(existing, field, case[field])
                        changed_fields.append(field)
                if changed_fields:
                    existing.save(update_fields=changed_fields)
                continue

            qctestsModel.objects.create(
                testcase_id=case["testcase_id"],
                test_type=case["test_type"],
                description=case["description"],
                steps=case["steps"],
                expected_outcome=case["expected_outcome"],
                tested_by_admin=False,
                tested_by_owner=False,
                admin_username="",
                owner_username="",
                study_id=study_id,
            )

    def _trigger_update_json_script(self):
        """
        Run the post-update script that refreshes derived study JSON artifacts.

        Returns:
            None
        """
        with open(config.update_notification_log_file, "w", encoding="utf-8") as log:
            try:
                execute_command = [
                    "python3",
                    f"{config.update_json_survey_script_path}",
                    f"{self.study_name}",
                ]
                result = subprocess.run(
                    execute_command,
                    stdout=log,
                    stderr=log,
                    text=True,
                    check=True,
                )
                logger.info("Study._trigger_update_json_script succeeded for study_name=%s", self.study_name)
                logger.debug("Study._trigger_update_json_script stdout=%s", result.stdout)
            except subprocess.CalledProcessError as exc:
                logger.info("Study._trigger_update_json_script failed for study_name=%s", self.study_name)
                logger.debug("Study._trigger_update_json_script error=%s", exc)

    def get_modified_json_form_csv(data):
        """
        Regroup study data rows by subject for modified JSON generation.

        Args:
            data (list): Study rows to regroup.

        Returns:
            tuple: Grouped JSON string and grouped subject count.
        """
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

    def zip_unused_sheets(self) -> None:
        """Zip up any unused subject PDFs for download."""
        logger.info("Study.zip_unused_sheets called for study_name=%s", self.study_name)
        try:
            study_df = read_study_df(self.study_name)
            enrolled_subject_list = get_user_list(study_df)
            logger.info(enrolled_subject_list)
        except (FileNotFoundError, KeyError, studyexceptions.EmptyStudyTableException):
            enrolled_subject_list = []

        study_root = os.path.join(settings.DASH_FOLDER, config.app_study_folder, self.study_name)
        sheets_path = os.path.join(study_root, config.sheets_folder)
        zip_path = os.path.join(study_root, config.zip_file)
        if os.path.isfile(zip_path):
            os.remove(zip_path)

        all_subjects_pdfs = np.array(os.listdir(sheets_path))
        enrolled_subjects_pdfs = np.array([enrolled_subject + '.pdf' for enrolled_subject in enrolled_subject_list])
        not_enrolled_subjects_pdfs = [
            os.path.join(sheets_path, not_enrolled_subject)
            for not_enrolled_subject in np.setdiff1d(all_subjects_pdfs, enrolled_subjects_pdfs)
        ]

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for pdf_path in not_enrolled_subjects_pdfs:
                if os.path.isfile(pdf_path):
                    zip_file.write(pdf_path, arcname=os.path.basename(pdf_path))

        logger.info("Study.zip_unused_sheets finished for study_name=%s", self.study_name)
        logger.debug("Study.zip_unused_sheets return_value=%s", zip_path)
        return zip_path

    def create_test_cases(self):
        """
        Public wrapper to generate default QC test cases for the study.

        Returns:
            None
        """
        logger.info("Study.create_test_cases called for study_name=%s", self.study_name)
        self._create_test_cases()
        logger.info("Study.create_test_cases finished for study_name=%s", self.study_name)
        logger.debug("Study.create_test_cases return_value=%s", None)

    def close(self) -> bool:
        """Archive the study folder and mark it closed in the DB."""
        logger.info("Study.close called for study_name=%s", self.study_name)
        archived = os.path.join(config.archive_folder, self.study_name)
        os.makedirs(archived, exist_ok=True)
        os.rename(self.path, os.path.join(archived, self.study_name))
        csv = config.csv_prefix + self.study_name + '.csv'
        csv_path = os.path.join(config.storage_folder, csv)
        if os.path.isfile(csv_path):
            os.rename(csv_path, os.path.join(archived, csv))
        result = close_study_model(self.study_name)
        logger.info("Study.close finished for study_name=%s", self.study_name)
        logger.debug("Study.close return_value=%s", result)
        return result

    @classmethod
    def list_all_for_user(cls, user) -> list:
        """Return a list of lightweight dicts for all studies this user can see."""
        logger.info("Study.list_all_for_user called for user=%s", user)
        raw = retrieve_all_studies_for_user(user)
        result = json.loads(raw)
        logger.info("Study.list_all_for_user finished for user=%s", user)
        logger.debug("Study.list_all_for_user return_value=%s", result)
        return result


def get_all_study_details(user):
    """
    Retrieve all study details and dashboard statistics for the home page.

    Args:
        user (User): User whose accessible studies should be loaded.

    Returns:
        tuple: Study metadata list, stats dictionary, and error message string.
    """
    logger.info("get_all_study_details called for user=%s", user)
    stats_json = {}
    total_study_dict = []
    error_message = ""

    for study in Study.list_all_for_user(user):
        try:
            study[constants.key_name_created_date] = study[constants.key_name_created_date]
            json_data = get_json_data(study[constants.key_name_study_title])            
            investigators, viewers = _get_study_group_members(study[constants.key_name_study_title], user)
            study["investigators"] = investigators
            study["viewers"] = viewers
            sensor_list_limited = json_data.get(constants.field_name_sensor_list_limited, [])
            study[constants.field_name_sensor_list_limited] = (
                sensor_list_limited if isinstance(sensor_list_limited, list) else []
            )
            number_of_subjects = Subject.count_pdfs(study[constants.key_name_study_title])
            study[constants.key_name_number_of_subjects] = number_of_subjects
            study["enrolled_subjects"] = json_data.get("number_of_enrolled_subjects", 0) or 0
            study["duration"] = json_data.get("duration", 0) or 0
            if number_of_subjects:
                study_stats = calculate_stats_of_number_of_subjects(
                    study[constants.key_name_study_title],
                    number_of_subjects,
                )
            else:
                study_stats = {}
            study[constants.key_name_stats] = study_stats
            stats_json[study[constants.key_name_study_title]] = study_stats
            if constants.key_name_sensor_list in json_data:
                raw_sensor_list = json_data.get(constants.key_name_sensor_list)
                if raw_sensor_list is None:
                    res = []
                elif isinstance(raw_sensor_list, str):
                    res = [raw_sensor_list]
                else:
                    res = list(raw_sensor_list)
                study[constants.key_name_sensor_list] = res

                if constants.key_name_survey in json_data:
                    res.append(constants.ema)
                if constants.field_name_labeling in json_data:
                    if json_data[constants.field_name_labeling] is not None and json_data[constants.field_name_labeling] > 0 :
                        res.append(constants.field_name_labeling)
                study[constants.key_name_sensor_list] = res  
                # study[constants.key_name_sensor_list] = study[constants.key_name_sensor_list].append(constants.ema)
                sensors = res
            else:
                sensors = ['ema']
            study['wearables'] = json_data.get('wearables', [])
            study[constants.key_name_current_sensor_list] = get_latest_received_study_sensor_details(study[constants.key_name_study_title])
            # to add old surveys with no ids in session and use for survey files listing
            survey_data = json_data.get(constants.key_name_survey)
            if isinstance(survey_data, dict):
                if "id" not in survey_data:
                    study["old_ema"]= True

            total_study_dict.append(study)

        except FileNotFoundError:
            logger.warning(
                "Study folder/json missing for study=%s",
                study.get(constants.key_name_study_title)
            )
            continue
        except EmptyDataError as ed:
            logger.info("Empty Data Error %s",ed)
            error_message = "Empty Data Error"
            continue
        except Exception:
            logger.exception(
                "Failed loading study=%s",
                study.get(constants.key_name_study_title)
            )
            continue
    #except Exception as e:
    #    logger.info("get_all_study_details::: Exception occurred %s",e)
    #    error_message = "Exception occurred"
    logger.info("get_all_study_details finished for user=%s", user)
    logger.debug(
        "get_all_study_details return_value=%s",
        (total_study_dict, stats_json, error_message),
    )
    return total_study_dict, stats_json,error_message
