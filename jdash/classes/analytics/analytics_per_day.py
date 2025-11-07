import os
from datetime import datetime
from . import activity_coding
import csv

time_now = datetime.strptime(datetime.now().strftime('ddmmmyyyy_HHMMSS'), 'ddmmmyyyy_HHMMSS')


def activityPerDay(dir_base, dir_save, enrollmentDate, study_duration):
    filename = 'Activity_per_day_in_min_' + time_now + '.csv'
    # listing the directories in  base folder aa = dir(dir_base);
    sub_dirs = os.listdir(dir_base)
    # sub_dirs = {aa(3:end).name}';
    # all enum keys _min extension is added and stored as header values
    activity_labels, activity_numbers = activity_coding.items()
    header = ['Subject_ID', 'Study_day', 'Date', activity_labels]

    table_activity_per_day = {}

    for dir in sub_dirs:
        # print(dir)
        os.path.join('FPListRec', dir_base, dir, 'activity.*.json')

    with open(filename, 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        writer.writerows(table_activity_per_day)


def distance_by_activity_per_day(dir_base, dir_save, enrollmentDate, activity_coding, study_duration):
    filename = 'Distance_by_Activity_per_day_in_meters_' + time_now + '.csv'
    table_distance_by_activity_per_day = {}
    sub_dirs = os.listdir(dir_base)


def distance_per_day(dir_base, dir_save, enrollmentDate, study_duration):
    filename = 'Distance_per_day_in_meters_' + time_now + '.csv'
    table_distance_per_day = {}
    sub_dirs = os.listdir(dir_base)


def phoneusage_by_category_per_day(dir_base, dir_save, enrollmentDate, appList, categoryList, study_duration):
    filename = 'phoneUsage_byCategory_per_day_in_min_' + time_now + '.csv'
    table_PhoneUsage_by_Category_per_day = {}
    sub_dirs = os.listdir(dir_base)
    for dir in sub_dirs:
        files_app_i = os.path.join('FPListRec', dir_base, dir, 'location.*.json')
        files_act_i = os.path.join('FPListRec', dir_base, dir, 'activity.*.json')
