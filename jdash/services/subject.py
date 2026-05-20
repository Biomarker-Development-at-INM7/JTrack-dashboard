#!/usr/bin/python
# -*- coding: utf-8 -*-
###########################################################################
####               subject.py
####           this file contains all the service methods related to subjects
####           initial version written by mstolz
####           modified by mnarava
####            Refactored and extended for clarity and robustness.
####
###########################################################################

import json
import logging
import os
import time
from django.conf import settings
from jdash.config import runtime_config as config
from jdash.config import constants as constants
import qrcode
import pdfkit
import pandas as pd
from jdash.utils.SubjectPDF import SubjectPDF
from datetime import datetime, timezone
logger = logging.getLogger("django")
timestamp_format = '%Y-%m-%d %H:%M:%S'

class Subject:
    """Class representing a Subject"""
    def __init__(self, obj,subject_json):
        """
        Initialize a subject view/service object from dashboard and JSON data.

        Args:
            obj (dict): Dashboard-derived subject row.
            subject_json (dict): Subject JSON metadata, if available.
        """
        self.subject_name = obj['subject_name']
        self.app = obj['app']
        self.status = obj['status_code']
        self.time_in_study = obj['time_in_study']
        self.date_registered = obj['date_registered']
        self.date_left_study = obj['date_left_study']
        self.n_batches = []
        self.last_times_received = []
        self.sensor_last_times_received = {}
        self.missing_data = False
        for (k, v) in obj.items():
            if k.endswith(' last_time_received'):
                sensor = k.rsplit(' ', 2)[0]
                self.sensor_last_times_received[sensor] = v
                self.last_times_received.append(v)
            elif k.startswith('last_time_received '):
                # Backward-compatible support for older reversed key order.
                sensor = k.split(' ', 1)[1]
                self.sensor_last_times_received[sensor] = v
                self.last_times_received.append(v)
        
        if self.app == 'ema' and 'last_time_received_ema' in obj:
            self.sensor_last_times_received['ema'] = obj['last_time_received_ema']
            self.last_times_received.append(obj['last_time_received_ema'])

        if subject_json is not None:
            self.study_enrolled_in = subject_json.get('studyId')

    def get_activity_status_code(self, study_obj):
        """
        activity status codes
        0: delayed sensor data (>= 2 days)
        1: left prematurely
        2: study duration reached, but not left
        3: study duration reached,  left
        4: multiple qr codes

        :param subject object and study object
        :return: activity_status_code
        """

        qr_id = self.subject_name
        activity_status_code = 0
        missing_data = False
        # Parse date_registered as aware datetime
        registered_timestamp_in_s = datetime.strptime(self.date_registered, timestamp_format).replace(
            tzinfo=timezone.utc)

        # left_timestamp_in_s already aware or None
        if self.date_left_study != 'none':
            dt_naive = datetime.strptime(self.date_left_study, timestamp_format)
            left_timestamp_in_s = dt_naive.replace(tzinfo=timezone.utc)
        else:
            left_timestamp_in_s = None

        # Use aware datetime for current time
        now_aware = datetime.now(timezone.utc)
        last_mandatory_send_in_s = now_aware if not left_timestamp_in_s else left_timestamp_in_s

        # Use last_mandatory_send_in_s and registered_timestamp_in_s (both aware)
        time_in_study_days = int(str(self.time_in_study).split(' ')[0])

        for last_time_received in self.last_times_received:
            correct_time_format = self.check_format_of_timestamp(last_time_received)
            if correct_time_format is None:
                continue  # Skip 'none' values safely

            ltr_in_s = (registered_timestamp_in_s if last_time_received
                        == 'none' else correct_time_format)
            days_since_last_received = (last_mandatory_send_in_s
                    - ltr_in_s).days

            if days_since_last_received >= 2:
                activity_status_code = 0
                missing_data = True

        if not left_timestamp_in_s:
            if self.check_multi_registration():
                activity_status_code = 4
            elif time_in_study_days > int(study_obj['duration']):
                activity_status_code = 2
            elif missing_data:
                activity_status_code = 0
        else:

                # self.ids_with_missing_data.append(qr_id)

            if (left_timestamp_in_s - registered_timestamp_in_s).days >= int(study_obj['duration']):
                activity_status_code = 3
            elif (left_timestamp_in_s - registered_timestamp_in_s).days < int(study_obj['duration']):
                activity_status_code = 1

        return activity_status_code

    def get_sensor_activity_code(self, value, study_obj):
        """
        activity status codes
        0: delayed sensor data while still in study (>= 2 days)
        1: study duration exceeded while still in study
        2: active / recently received sensor data
        3: subject has left study; stream treated as closed
        4: no sensor data received yet

        :param subject object and study object
        :return: activity_status_code
        """
        sensors_dict = {}
        today = datetime.now(timezone.utc)  # timezone-aware datetime

        registered_timestamp_in_s = datetime.strptime(self.date_registered, timestamp_format).replace(
            tzinfo=timezone.utc)
        if self.date_left_study != 'none':
            left_timestamp_in_s = datetime.strptime(self.date_left_study, timestamp_format).replace(tzinfo=timezone.utc)
        else:
            left_timestamp_in_s = None

        last_mandatory_send_in_s = today if not left_timestamp_in_s else left_timestamp_in_s

        time_in_study_days = int(str(self.time_in_study).split(' ')[0])
        dashboard_sensor_list = (study_obj or {}).get("dashboard_sensor_list")
        if dashboard_sensor_list is None:
            allowed_sensors = None
        else:
            allowed_sensors = {
                str(sensor).strip().lower()
                for sensor in (dashboard_sensor_list or [])
            }
            if self.app == 'ema':
                allowed_sensors.add('ema')
            if not allowed_sensors:
                return {}

        # Send a dictionary with sensor as key, and a value dictionary with tool tip desc and code
        for (k, value) in self.sensor_last_times_received.items():
            if allowed_sensors is not None and str(k).strip().lower() not in allowed_sensors:
                continue
            sensor_activity_dict = {
                'sensor_code': constants.sensor_list.get(k, k),
                'days_since_received': None,
            }

            if self._is_missing_sensor_value(value):
                sensor_activity_dict['status_code'] = 4
                sensor_activity_dict['status_desc'] = constants.no_sensor_not_received
            elif left_timestamp_in_s is not None:
                sensor_activity_dict['status_code'] = 3
                if (left_timestamp_in_s - registered_timestamp_in_s).days < int(study_obj['duration']):
                    sensor_activity_dict['status_desc'] = constants.no_sensor_left_early
                else:
                    sensor_activity_dict['status_desc'] = constants.no_sensor_duration_reached
            elif time_in_study_days > int(study_obj['duration']):
                sensor_activity_dict['status_code'] = 1
                sensor_activity_dict['status_desc'] = constants.no_sensor_duration_exceeded
            else:
                sensor_ltr_in_s = self.check_format_of_timestamp(value)

                # Use 'today' here directly (it's timezone aware)
                days_since_last_received = (today - sensor_ltr_in_s).days
                sensor_activity_dict['days_since_received'] = days_since_last_received

                if days_since_last_received >= 2:
                    sensor_activity_dict['status_code'] = 0
                    sensor_activity_dict['status_desc'] = constants.no_sensor_data
                else:
                    sensor_activity_dict['status_code'] = 2
                    sensor_activity_dict['status_desc'] = constants.sensor_data_active

            sensors_dict[k] = sensor_activity_dict

        return sensors_dict

    @staticmethod
    def _is_missing_sensor_value(value):
        """
        Normalize dashboard "no timestamp" variants.

        Args:
            value: Raw last_time_received value.

        Returns:
            bool: True when the value represents an absent timestamp.
        """
        if value is None:
            return True
        normalized = str(value).strip().lower()
        return normalized in {"", "none", "null"}

    def check_format_of_timestamp(self, last_time_received):
        """
        Normalize a timestamp value into a timezone-aware datetime.

        Args:
            last_time_received (str): Timestamp string or ``none`` marker.

        Returns:
            datetime | None: Parsed timezone-aware datetime or ``None`` for missing values.
        """
        if self._is_missing_sensor_value(last_time_received):
            return None
        if "-" in last_time_received:
            dt = datetime.strptime(last_time_received, timestamp_format)
            return dt.replace(tzinfo=timezone.utc)  # Make aware
        return datetime.fromtimestamp(int(last_time_received), tz=timezone.utc)


    def check_multi_registration(self):
        """
        check if there are multiple registrations (active qr codes) of one user. 
        Look if more than one entry of date_left_study is empty
        :return: true if multiple qr codes are active
        """
        if isinstance(self.date_left_study, (list, pd.Series)):
            not_left = [x for x in self.date_left_study if x == '']
            return len(not_left) > 1
        elif isinstance(self.date_left_study, str):
            # A string can't have multiple active registrations, return False
            return False
        return False

    @staticmethod
    def load_details(study_name, subject_id):
        """
        Load the subject JSON details for a study subject.

        Args:
            study_name (str): Name of the study.
            subject_id (str): Subject identifier.

        Returns:
            dict: Parsed subject JSON metadata or an empty dict when unavailable.
        """
        logger.debug("Subject.load_details called for study_name=%s subject_id=%s", study_name, subject_id)
        subject_json_path = os.path.join(config.users_folder, study_name + '_'
                                    + subject_id + '.json')
        try:
            with open(subject_json_path,'r',encoding=constants.encoding) as f:
                user_data = json.load(f)
        except FileNotFoundError:
            logging.error("File not found: %s",subject_json_path)
            user_data = {}
        except json.JSONDecodeError:
            logging.error("Invalid JSON format: %s",subject_json_path)
            user_data = {}

        logger.debug("Subject.load_details finished for study_name=%s subject_id=%s", study_name, subject_id)
        logger.debug("Subject.load_details return_value=%s", user_data)
        return user_data

    @staticmethod
    def create_pdfs_for_study(study_name, number_to_create):
        """
        Create subject QR/PDF artifacts for the given study.

        Args:
            study_name (str): Name of the study.
            number_to_create (int): Number of new subject artifacts to create.

        Returns:
            int: Final subject count after creation.
        """
        logger.info(
            "Subject.create_pdfs_for_study called for study_name=%s number_to_create=%s",
            study_name,
            number_to_create,
        )
        count = Subject.count_pdfs(study_name)
        start_number = count if count > 0 else 1
        end_number = number_to_create + 1 if count > 0 else number_to_create
        for subject_number in range(start_number, start_number + end_number):
            subject_name = study_name + '_'  + str(subject_number).zfill(config.max_subjects_exp)
            pdf_path = os.path.join(
                settings.DASH_FOLDER,
                config.app_study_folder,
                study_name,
                config.sheets_folder,
                subject_name + '.pdf'
            )
            if os.path.isfile(pdf_path):
                continue

            Subject.create_qr_codes(study_name, subject_name)
            Subject.write_pdf(study_name, subject_name)
            os.chown(pdf_path, 33, 3619)
        result = start_number + number_to_create
        logger.info("Subject.create_pdfs_for_study finished for study_name=%s", study_name)
        logger.debug("Subject.create_pdfs_for_study return_value=%s", result)
        return result

    @staticmethod
    def count_pdfs(study_name):
        """
        Count the number of generated subject QR/PDF sheets for a study.

        Args:
            study_name (str): Name of the study.

        Returns:
            int: Number of generated subject files.
        """
        logger.info("Subject.count_pdfs called for study_name=%s", study_name)
        path = os.path.join(
            settings.DASH_FOLDER,
            config.app_study_folder,
            study_name,
            config.sheets_folder
        )
        if os.path.exists(path):
            contents = os.listdir(path)
            result = len(contents)
            logger.info("Subject.count_pdfs finished for study_name=%s", study_name)
            logger.debug("Subject.count_pdfs return_value=%s", result)
            return result
        logger.info("Subject.count_pdfs finished for study_name=%s", study_name)
        logger.debug("Subject.count_pdfs return_value=%s", 0)
        return 0

    @staticmethod
    def remove_from_study(study_name, subject_to_remove):
        """
        Remove a subject from the study by updating the subject JSON status.

        Args:
            study_name (str): Name of the study.
            subject_to_remove (str): Subject identifier including modality suffix.

        Returns:
            None
        """
        logger.info(
            "Subject.remove_from_study called for study_name=%s subject_to_remove=%s",
            study_name,
            subject_to_remove,
        )
        os.setuid(33)
        (subject_id, app) = str(subject_to_remove).split(constants.sep)
        user_json_path = os.path.join(config.users_folder, study_name + '_' + subject_id + '.json')
        time_left = int(round(time.time() * 1000))

        time_left_key = 'time_left' + constants.suffix_per_modality_dict[app]
        status_key = 'status' + constants.suffix_per_modality_dict[app]

        with open(user_json_path,'r',encoding=constants.encoding) as f:
            user_data = json.load(f)

        user_data[time_left_key] = time_left
        user_data[status_key] = constants.remove_status_code

        with open(user_json_path, 'w',encoding=constants.encoding) as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)
        logger.info("Subject.remove_from_study finished for study_name=%s", study_name)
        logger.debug("Subject.remove_from_study return_value=%s", None)

    @staticmethod
    def create_qr_codes(study_id, subject_name):
        """
        Create QR-code PNGs for all activations of a subject.

        Args:
            study_id (str): Name or identifier of the study.
            subject_name (str): Subject identifier.

        Returns:
            None
        """
        logger.info("Subject.create_qr_codes called for study_id=%s subject_name=%s", study_id, subject_name)
        qr_path = os.path.join(settings.DASH_FOLDER, config.app_study_folder, study_id, config.qr_folder)
        for activation_number in range(1, config.number_of_activations + 1):
            user_activation_number = subject_name + '_'  + str(activation_number)

            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            data = 'https://jdash.inm7.de?username=%s&studyid=%s' % (user_activation_number, study_id)

            qr.add_data(data)
            qr.make(fit=True)

            img = qr.make_image()
            img.save(os.path.join(qr_path, user_activation_number + '.png'))
        logger.info("Subject.create_qr_codes finished for study_id=%s subject_name=%s", study_id, subject_name)
        logger.debug("Subject.create_qr_codes return_value=%s", None)

    @staticmethod
    def write_pdf(study_id, subject_name):
        """
        Generate a subject PDF based on QR codes and subject information.

        Args:
            study_id (str): Name or identifier of the study.
            subject_name (str): Subject identifier.

        Returns:
            None
        """
        logger.info("Subject.write_pdf called for study_id=%s subject_name=%s", study_id, subject_name)
        qr_codes_path = os.path.join(
            settings.DASH_FOLDER,
            config.app_study_folder,
            study_id,
            config.qr_folder,
            subject_name
        )
        pdf_path = os.path.join(
            settings.DASH_FOLDER,
            config.app_study_folder,
            study_id,
            config.sheets_folder,
            subject_name + '.pdf'
        )

        pdf = SubjectPDF(study_id)
        pdf_string = "<html>"
        pdf_string += pdf.header()
        pdf_string += "<body>"
        pdf_string += pdf.draw_input_line_filled('Subject ID', subject_name)
        pdf_string += pdf.draw_input_line('Clinical ID')
        pdf_string += "<br><br>"
        pdf_string += pdf.qr_codes(qr_codes_path)
        pdf_string += "</body></html>"
        pdfkit.from_string(pdf_string, pdf_path, options={"enable-local-file-access": ""})
        os.chmod(pdf_path, 0o0775)
        logger.info("Subject.write_pdf finished for study_id=%s subject_name=%s", study_id, subject_name)
        logger.debug("Subject.write_pdf return_value=%s", None)
