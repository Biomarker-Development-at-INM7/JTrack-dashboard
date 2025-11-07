#!/usr/bin/python
# -*- coding: utf-8 -*-
###########################################################################
####               subject.py
####           this file contains all the service methods related to subjects
####           initial version written by mstolz
####           modified by mnarava
####
####
###########################################################################

import os,logging,json,time
from jdash.apps import jdashConfig as config
from jdash.apps import constants as constants
import qrcode
import pdfkit
from jdash.classes.SubjectPDF import SubjectPDF
from datetime import datetime
logger = logging.getLogger("django")
timestamp_format = '%Y-%m-%d %H:%M:%S'




class Subject:
    """Class representing a Subject"""
    def __init__(self, obj,subject_json):
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
            if k.find('last_time_received') != -1:
                sensor = k.split(' ')[0]
                self.sensor_last_times_received[sensor] = v
                self.last_times_received.append(v)

        if subject_json is not None:
            self.study_enrolled_in = subject_json['studyId']

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
        registered_timestamp_in_s =  datetime.strptime(self.date_registered, timestamp_format)
        left_timestamp_in_s = (datetime.strptime(self.date_left_study,
                               timestamp_format) if self.date_left_study
                               != 'none' else None)

        last_mandatory_send_in_s = (datetime.now().astimezone() if not left_timestamp_in_s else left_timestamp_in_s)
        time_in_study_days = int(str(self.time_in_study).split(' ')[0])

        for last_time_received in self.last_times_received:

            correct_time_format = self.check_format_of_timestamp(last_time_received)

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
        0: delayed sensor data (>= 2 days)
        1: left prematurely
        2: study duration reached, but not left
        3: study duration reached,  left
        4: multiple qr codes

        :param subject object and study object
        :return: activity_status_code
        """
        sensors_dict = {}
        missing_data = False
        today = datetime.now().astimezone()

        today_in_s = datetime.strptime(today.strftime(timestamp_format),
                              timestamp_format)

        registered_timestamp_in_s = datetime.strptime(self.date_registered, timestamp_format)
        left_timestamp_in_s = (datetime.strptime(self.date_left_study,
                               timestamp_format) if self.date_left_study
                               != 'none' else None)

        last_mandatory_send_in_s =  (today if not left_timestamp_in_s else left_timestamp_in_s)

        time_in_study_days = int(str(self.time_in_study).split(' ')[0])

        # current date and time

        # Send a dictionary with sensor as key, and a value dictionary with tool tip desc and code

        for (k, value) in self.sensor_last_times_received.items():
            sensor_activity_dict = {}
            if value != 'none':
                sensor_activity_dict['sensor_code'] =  constants.sensor_list[k]  

                sensor_ltr_in_s = self.check_format_of_timestamp(value)
                    
                days_since_last_received = (today_in_s
                            - sensor_ltr_in_s).days

                if time_in_study_days >= int(study_obj['duration']):
                    sensor_activity_dict['status_code'] = 3
                    sensor_activity_dict['status_desc'] = constants.no_sensor_duration_reached

                # left_timestamp_in_s can be none

                if left_timestamp_in_s is not None:
                    if (left_timestamp_in_s
                        - registered_timestamp_in_s).days  < int(study_obj['duration']):
                        sensor_activity_dict['status_code'] = 1
                        sensor_activity_dict['status_desc'] = constants.no_sensor_left_early

                if days_since_last_received < int(study_obj['duration'
                        ]) and days_since_last_received >= 2:
                    sensor_activity_dict['status_code'] = 0
                    sensor_activity_dict['status_desc'] = constants.no_sensor_data

                if days_since_last_received < 2:
                    sensor_activity_dict['status_code'] = 2
                    sensor_activity_dict['status_desc'] = constants.sensor_data_active

                if 'status_code' not in sensor_activity_dict:
                    sensor_activity_dict['status_code'] = 'none'
                if 'status_desc' not in sensor_activity_dict:
                    sensor_activity_dict['status_desc'] = 'none'

                sensor_activity_dict['days_since_received'] = days_since_last_received
                sensors_dict[k] = sensor_activity_dict

        return sensors_dict

    def check_format_of_timestamp(self,last_time_received):
        """
        check format of timestamp 
        return the string or changed format
        """
        
        if "-" in last_time_received :
            return datetime.strptime(last_time_received,
                        timestamp_format)
        return datetime.fromtimestamp(last_time_received)

    def check_multi_registration(self):
        """
        check if there are multiple registrations (active qr codes) of one user. 
        Look if more than one entry of date_left_study is empty
        :return: true if multiple qr codes are active
        """

        time_left_col = self.date_left_study
        not_left = time_left_col[time_left_col == '']
        if len(not_left) > 1:
            return True
        return False


def get_subject_details(study_name,subject_id):
    """
    loads the subject json details

    :return:
    """
    subject_json_path = os.path.join(config.users_folder, study_name + '_'
                                + subject_id + '.json')
    try:
        with open(subject_json_path,'r',encoding='utf-8') as f:
            user_data = json.load(f)
    except FileNotFoundError:
        logging.error("File not found: %s",subject_json_path)
        user_data = {}
    except json.JSONDecodeError:
        logging.error("Invalid JSON format: %s",subject_json_path)
        user_data = {}

    return user_data

def create_subjects_for_study(study_name, number_to_create):
    """
    creates one subject, if he or she exists return

    :return:
    """
    count = count_number_of_subject_pdf(study_name)
    start_number = count if count > 0 else 1
    end_number = number_to_create + 1 if count > 0 else number_to_create
    for subject_number in range(start_number, start_number
                                + end_number):
        subject_name = study_name + '_'  + str(subject_number).zfill(config.max_subjects_exp)
        if os.path.isfile(os.path.join(config.dash_folder,
                          config.app_study_folder, study_name,
                          config.sheets_folder, subject_name + '.pdf')):
            continue
        else:
            create_qr_codes(study_name, subject_name)
            write_to_pdf(study_name, subject_name)
        os.chown(os.path.join(config.dash_folder, config.app_study_folder, study_name,config.sheets_folder, subject_name + '.pdf'), 33, 3619)	
    return start_number + number_to_create


def count_number_of_subject_pdf(study_name):
    """
    counts number of user qr sheets created

    :return:
    """
    path = os.path.join(config.dash_folder,
                          config.app_study_folder, study_name,
                          config.sheets_folder)
    if os.path.exists(path):
        contents = os.listdir(os.path.join(config.dash_folder,
							config.app_study_folder, study_name,
							config.sheets_folder))
        return len(contents)
    return 0



def remove_subjects_for_study(study_name, subject_to_remove):
    """
    Remove the subjects from the study
    Update the status to 3

    :return:
    """
    logger.info("remove_subjects_for_study")
    os.setuid(33)
    (subject_id, app) = str(subject_to_remove).split(constants.sep)
    user_json_path = os.path.join(config.users_folder, study_name + '_'
                                  + subject_id + '.json')
    time_left = int(round(time.time() * 1000))

    time_left_key = 'time_left' + constants.suffix_per_modality_dict[app]
    status_key = 'status' + constants.suffix_per_modality_dict[app]

    with open(user_json_path,'r',encoding='utf-8') as f:
        user_data = json.load(f)

    user_data[time_left_key] = time_left
    user_data[status_key] = constants.remove_status_code

    with open(user_json_path, 'w',encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)


def create_qr_codes(study_id, subject_name):
    """
    Function to create a QR-code which corresponds to the new subject given. The Code will be stored in a .png.

    :return:
    """

    qr_path = os.path.join(config.dash_folder, config.app_study_folder,
                           study_id, config.qr_folder)
    for activation_number in range(1, config.number_of_activations + 1):
        user_activation_number = subject_name + '_'  + str(activation_number)

        qr = qrcode.QRCode(version=1,
                           error_correction=qrcode.constants.ERROR_CORRECT_H,
                           box_size=10, border=4)
        data = 'https://jdash.inm7.de?username=%s&studyid=%s' % (user_activation_number, study_id)

        # data = "http://locahost:8000?username=%s&studyid=%s" % (user_activation_number, study_id)

        # Add data

        qr.add_data(data)
        qr.make(fit=True)

        # Create an image from the QR Code instance

        img = qr.make_image()

        # Save it somewhere, change the extension as needed:

        img.save(os.path.join(qr_path, user_activation_number + '.png'))


def write_to_pdf(study_id, subject_name):
    """
....Function to generate a pdf based on QR-Code and other information.

....:return:
...."""

    qr_codes_path = os.path.join(config.dash_folder,
                                 config.app_study_folder, study_id,
                                 config.qr_folder, subject_name)
    pdf_path = os.path.join(config.dash_folder,
                            config.app_study_folder, study_id,
                            config.sheets_folder, subject_name + '.pdf')

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
    #pdf.add_page()

    #pdf.draw_input_line_filled('Subject ID', subject_name)
    #pdf.draw_input_line('Clinical ID')
    #pdf.ln(10)

    #pdf.line(pdf.get_x(), pdf.get_y(), pdf.get_x() + 190, pdf.get_y())
    #pdf.ln(15)

    #pdf.qr_codes(qr_codes_path)

    #pdf.output(pdf_path)
