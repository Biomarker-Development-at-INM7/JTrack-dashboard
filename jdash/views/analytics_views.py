import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import StreamingHttpResponse
from django.shortcuts import render
from django.utils.encoding import escape_uri_path

from jdash.analytics.data.raw_subject_data import (
    RawSubjectDataError,
    RawSubjectDataNotFound,
    RawSubjectDataValidationError,
)
from jdash.analytics.data.raw_subject_gateway import subject_raw_download
from jdash.analytics.data.study_metadata import get_analytics_study_json
from api.permissions import visible_studies_for_user
from jdash.config import constants as constants
from jdash.repositories.study_repository import retrieve_all_studies_for_user

from jdash.utils.fileutils import build_wearable_dashboard_sensor_name, to_list
from jdash.views.message_helpers import forbidden_with_message

logger = logging.getLogger("django")


@login_required
def download_subject_raw_data(request, study_name, subject_id):
    """Stream one subject's raw folder to an authorized dashboard user."""
    study_exists = visible_studies_for_user(request.user).filter(title=study_name).exists()
    if not study_exists:
        return forbidden_with_message(
            request,
            "You do not have permission to download data from this study.",
        )

    try:
        stream, filename, content_type = subject_raw_download(study_name, subject_id)
        response = StreamingHttpResponse(
            stream,
            content_type=content_type,
        )
    except (RawSubjectDataNotFound, RawSubjectDataValidationError) as exc:
        messages.error(request, str(exc), fail_silently=True)
        return render(request, constants.error_page, status=404)
    except RawSubjectDataError as exc:
        logger.warning(
            "Raw subject data download unavailable for study=%s subject=%s: %s",
            study_name,
            subject_id,
            exc,
        )
        messages.error(
            request,
            "Raw data is temporarily unavailable.",
            fail_silently=True,
        )
        return render(request, constants.error_page, status=503)

    response["Content-Disposition"] = (
        f"attachment; filename*=UTF-8''{escape_uri_path(filename)}"
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _append_unique_sensor(sensor_list, sensor_name):
    sensor_name = str(sensor_name or "").strip()
    if sensor_name and sensor_name not in sensor_list:
        sensor_list.append(sensor_name)


def _append_wearable_sensors(sensor_list, study_data):
    for wearable in study_data.get("wearables", []) or []:
        if not isinstance(wearable, dict):
            continue
        wearable_name = wearable.get("sensorname", "")
        for sensor in wearable.get("sensors", []) or []:
            if not isinstance(sensor, dict):
                continue
            wearable_sensor_name = build_wearable_dashboard_sensor_name(
                wearable_name,
                sensor.get("wearable_sensor", ""),
            )
            _append_unique_sensor(sensor_list, wearable_sensor_name)


@login_required
def analytics(request, study_name):
    """
    Handles the analytics view for the given study.

    This view retrieves the studies available to the logged-in user, builds
    the initial study and sensor payload expected by the analytics frontend,
    and renders the analytics details page.

    Args:
        request (HttpRequest): The HTTP request object.
        study_name (str): Study name to display analytics for.

    Returns:
        HttpResponse: The rendered analytics details page.
    """
    if study_name != "all" and not visible_studies_for_user(request.user).filter(title=study_name).exists():
        return forbidden_with_message(
            request,
            "You do not have permission to view analytics for this study.",
        )

    context = {}
    sensors_map = {}
    study_list = []
    study_dict = retrieve_all_studies_for_user(request.user)
    for study in json.loads(study_dict):
        study_list.append(study[constants.key_name_study_title])
        sensor_list = to_list(study.get(constants.key_name_sensor_list))
        has_ema = study.get(constants.key_name_survey) not in [None, ""]

        try:
            json_data = get_analytics_study_json(study[constants.key_name_study_title])
            raw_sensor_list = json_data.get(constants.key_name_sensor_list)
            if raw_sensor_list is not None:
                if isinstance(raw_sensor_list, str):
                    sensor_list = [raw_sensor_list]
                else:
                    sensor_list = list(raw_sensor_list)
            _append_wearable_sensors(sensor_list, json_data)
            has_ema = has_ema or bool(json_data.get(constants.key_name_survey))
        except FileNotFoundError:
            logger.info(
                "analytics:: no study json found for %s; falling back to db sensor list",
                study[constants.key_name_study_title],
            )

        if has_ema:
            _append_unique_sensor(sensor_list, constants.ema)

        sensors_map[study[constants.key_name_study_title]] = sensor_list
    selected_study_name = "all" if study_name == "all" else study_name.lower()
    context = {
        constants.key_name_study_name: selected_study_name,
        constants.key_name_session_id: request.session.session_key,
        "has_studies": bool(study_list),
        'initial_args': {
            "study-store": {
                "data": study_list
            },
            "sensor-store": {
                "data": sensors_map
            }
        }
    }
    logger.debug("analytics:: study name %s", context)
    return render(request, constants.analytics_details_page, context=context)
