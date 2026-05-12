import json
import logging

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_str

from auditlog.models import LogEntry

from jdash.config import constants as constants
from jdash.models import (
    DeviceSensor,
    FileDownloadToken as downloadFile,
    QualityControlTests as qctestsModel,
    # ResolutionCatalog,
    SamplingRateCatalog,
    Study as studymodel,
    StudyDeviceSensor,
    Survey as surveyModel,
    Task,
    UnitCatalog,
)
from jdash.utils.utils import custom_serializer

logger = logging.getLogger("django")


def set_email_for_user(username, email):
    """Set the email address for a user account."""
    user = User.objects.get(username=username)
    user.email = email
    user.save()


def retrieve_all_studies_for_user(user):
    """Return serialized studies visible to the given user."""
    queryset = studymodel.objects.none()
    group_names = [gp.name for gp in user.groups.all()]

    if "administrator" in group_names:
        queryset = studymodel.objects.filter(closed=False)
    else:
        combined_query = Q()
        for group_name in group_names:
            search_string = group_name.split("_group")[0]
            combined_query |= Q(title__startswith=search_string, closed=False)
        queryset = studymodel.objects.filter(combined_query)

    return custom_serializer(queryset.values())


def log_action(user, obj, action_flag, message):
    """Create an auditlog entry for the given object."""
    LogEntry.objects.log_action(
        user_id=user.pk,
        content_type_id=ContentType.objects.get_for_model(obj).pk,
        object_id=obj.pk,
        object_repr=force_str(obj)[:200],
        action_flag=action_flag,
        change_message=message,
    )


@transaction.atomic
def persist_study_device_sensors(study, user, rows):
    """Create StudyDeviceSensor rows from submitted device rows."""
    for row in rows:
        ds = DeviceSensor.objects.get(pk=row["device_sensor_id"])
        # Resolution support is currently disabled in the study UI.
        # resolution = (
        #     ResolutionCatalog.objects.get(pk=row["resolution_id"])
        #     if row["resolution_id"]
        #     else ds.default_resolution
        # )
        sampling_rate = (
            SamplingRateCatalog.objects.get(pk=row["sampling_rate_id"])
            if row["sampling_rate_id"]
            else ds.default_sampling_rate
        )
        unit = (
            UnitCatalog.objects.get(pk=row["unit_id"])
            if row["unit_id"]
            else ds.default_unit
        )

        StudyDeviceSensor.objects.create(
            study=study,
            device_sensor=ds,
            sampling_rate=sampling_rate,
            unit=unit,
            is_enabled=True,
            notes="",
        )


def persist_task_list(study, task_rows):
    """Create task rows for a study."""
    for index, row in enumerate(task_rows, start=1):
        Task.objects.create(
            study=study,
            task_name=row["task_name"],
            task_description=row["task_description"],
            task_duration=row["task_duration"],
            task_preparation=row["task_preparation"],
            task_preparation_text=row["task_preparation_text"],
            sortId=index,
        )


def sync_task_list(study, task_rows):
    """Replace a study's task list with the submitted rows."""
    Task.objects.filter(study=study).order_by("id").delete()
    persist_task_list(study, task_rows)


def sync_study_device_sensors(study, rows):
    """Synchronize StudyDeviceSensor rows for a study."""
    existing_rows = {
        obj.device_sensor_id: obj
        for obj in StudyDeviceSensor.objects.filter(study=study)
    }
    submitted_device_sensor_ids = set()

    for row in rows:
        device_sensor_id = row["device_sensor_id"]
        submitted_device_sensor_ids.add(device_sensor_id)

        ds = DeviceSensor.objects.get(pk=device_sensor_id)
        # Resolution support is currently disabled in the study UI.
        # resolution = (
        #     ResolutionCatalog.objects.get(pk=row["resolution_id"])
        #     if row["resolution_id"]
        #     else ds.default_resolution
        # )
        sampling_rate = (
            SamplingRateCatalog.objects.get(pk=row["sampling_rate_id"])
            if row["sampling_rate_id"]
            else ds.default_sampling_rate
        )
        unit = (
            UnitCatalog.objects.get(pk=row["unit_id"])
            if row["unit_id"]
            else ds.default_unit
        )

        if device_sensor_id in existing_rows:
            study_device_sensor = existing_rows[device_sensor_id]
            # study_device_sensor.resolution = resolution
            #study_device_sensor.resolution = None
            study_device_sensor.sampling_rate = sampling_rate
            study_device_sensor.unit = unit
            study_device_sensor.is_enabled = True
            study_device_sensor.notes = ""
            study_device_sensor.save()
        else:
            StudyDeviceSensor.objects.create(
                study=study,
                device_sensor=ds,
                sampling_rate=sampling_rate,
                unit=unit,
                is_enabled=True,
                notes="",
            )

    for device_sensor_id, study_device_sensor in existing_rows.items():
        if device_sensor_id not in submitted_device_sensor_ids:
            study_device_sensor.delete()


def get_group_name_for_user(user):
    """Resolve the primary dashboard group mapping for the user."""
    group = constants.default_group
    group_names = [gp.name for gp in user.groups.all()]

    for group_name in group_names:
        if group_name in constants.group_mapping:
            group = constants.group_mapping[group_name]
            break
    return group


def create_new_study_in_db(user, form_data, survey, images_url):
    """Create a study record and its related DB rows."""
    logger.info("create_new_study_in_db %s", form_data)
    frequency = form_data[constants.field_name_frequency]
    labeling = form_data[constants.field_name_labeling]
    sensor_list = form_data[constants.field_name_sensor_list]

    study = studymodel.objects.create(
        title=form_data["name"],
        description=form_data["description"],
        numberOfSubjects=form_data["number-of-subjects"],
        enrolled_subjects="000",
        duration=form_data["duration"],
        is_test=form_data["is_test"],
        owner=user,
        passive_monitoring=True if len(sensor_list) > 0 else False,
        frequency=frequency,
        labeling=labeling,
        sensor_list=sensor_list,
        ecological_momentary_assessment=True if survey is not None else False,
        survey=survey,
        images=images_url,
    )

    persist_task_list(study, form_data.get("task_list", []))
    persist_study_device_sensors(study, user, form_data.get("device_sensor_rows", []))
    create_new_study_group(user, form_data)


def create_new_study_group(user, form_data):
    """Create the per-study group and assign creator permissions."""
    study_group, _created = Group.objects.get_or_create(name=form_data["name"] + "_group")
    assign_all_group_permissions(user.username, study_group.name)


@transaction.atomic
def update_study_db_details(form_data):
    """Update a study row and its related task/device rows."""
    survey_obj = None
    survey_value = form_data.get("survey")
    if survey_value not in (None, ""):
        survey_obj = surveyModel.objects.get(pk=survey_value)

    study = get_object_or_404(studymodel, title=form_data["name"])
    study.description = form_data["description"]
    study.duration = form_data["duration"]
    study.numberOfSubjects = form_data["number_of_subjects"]
    study.is_test = form_data[constants.field_name_is_test]
    study.enrolled_subjects = len(form_data["enrolled_subjects"])
    study.passive_monitoring = len(form_data[constants.field_name_sensor_list]) > 0
    study.frequency = form_data[constants.field_name_frequency]
    study.labeling = form_data[constants.field_name_labeling]
    study.sensor_list = form_data[constants.field_name_sensor_list]
    study.ecological_momentary_assessment = form_data["ema_checkbox"]
    study.survey = survey_obj if form_data["ema_checkbox"] else None
    study.save()

    sync_task_list(study, form_data.get("task_list", []))
    sync_study_device_sensors(study, form_data.get("device_sensor_rows", []))


def assign_all_group_permissions(username, groupname):
    """Assign the standard study permissions to the study group."""
    logged_user = User.objects.get(username=username)
    user_group = Group.objects.get(name=groupname)
    creator_permissions = [
        Permission.objects.get(name="Can add study"),
        Permission.objects.get(name="Can change study"),
        Permission.objects.get(name="Can delete study"),
        Permission.objects.get(name="Can view study"),
    ]

    user_group.user_set.add(logged_user)
    user_group.permissions.set(creator_permissions)


def close_study_model(study_name):
    """Mark the given study as closed."""
    study = get_object_or_404(studymodel, title=study_name)
    study.closed = 1
    study.save()
    ct = ContentType.objects.get_for_model(studymodel)
    LogEntry.objects.filter(
        content_type=ct,
        object_pk=str(study.pk),
    ).select_related("actor", "content_type").order_by("-timestamp")
    return True


def add_verification_code(code, token):
    """Store the generated verification code on a file download token."""
    downloadFile.objects.filter(token=token).update(code=code)
    return True


def retrieve_test_cases_for_study(study_db_id):
    """Return all quality-control test cases for a study."""
    results = qctestsModel.objects.filter(study_id=study_db_id).values()
    return json.dumps(list(results), default=str)


def update_test_case_flags(testcase_updates, username):
    """Update admin/owner completion flags for quality-control test cases."""
    success_count = 0
    failure_count = 0
    errors = []
    logger.info(testcase_updates)

    for test_case in testcase_updates:
        try:
            logger.info("An test %s %s", test_case, type(test_case))
            db_test_case = qctestsModel.objects.get(id=test_case["id"])
            db_test_case.tested_by_admin = test_case.get(
                "tested_by_admin",
                db_test_case.tested_by_admin,
            )
            db_test_case.tested_by_owner = test_case.get(
                "tested_by_owner",
                db_test_case.tested_by_owner,
            )
            db_test_case.admin_username = username
            db_test_case.save()
            success_count += 1
        except Exception as exc:
            logger.info(
                "An error occurred while updating Test Case %s: %s",
                test_case["id"],
                exc,
            )
            failure_count += 1

    return {
        "success_count": success_count,
        "failure_count": failure_count,
        "errors": errors,
    }


def retrieve_study_details_by_title(study_name):
    """Return serialized study details for a study title."""
    study = studymodel.objects.filter(title=study_name).values()
    return json.dumps(study[0], default=str)

