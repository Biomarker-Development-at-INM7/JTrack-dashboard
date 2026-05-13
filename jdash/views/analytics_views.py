import json
import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from jdash.config import constants as constants
from jdash.repositories.study_repository import retrieve_all_studies_for_user
from jdash.utils.fileutils import to_list
from jdash.utils.utils import get_json_data
logger = logging.getLogger("django")


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
    context = {}
    sensors_map = {}
    study_list = []
    study_dict = retrieve_all_studies_for_user(request.user)
    for study in json.loads(study_dict):
        sensor_list = []
        study_list.append(study[constants.key_name_study_title])
        sensor_list = to_list(study[constants.key_name_sensor_list])
        has_ema = study.get(constants.key_name_survey) not in [None, ""]

        try:
            json_data = get_json_data(study[constants.key_name_study_title])
            raw_sensor_list = json_data.get(constants.key_name_sensor_list)
            if raw_sensor_list is not None:
                if isinstance(raw_sensor_list, str):
                    sensor_list = [raw_sensor_list]
                else:
                    sensor_list = list(raw_sensor_list)
            has_ema = has_ema or constants.key_name_survey in json_data
        except FileNotFoundError:
            logger.info(
                "analytics:: no study json found for %s; falling back to db sensor list",
                study[constants.key_name_study_title],
            )

        if has_ema and constants.ema not in sensor_list:
            sensor_list.append(constants.ema)
        sensors_map[study[constants.key_name_study_title]] = sensor_list
    if study_name == "all":
        context[constants.key_name_study_name] = "all"
    else:
        context[constants.key_name_study_name] = study_name.lower()
    context[constants.key_name_session_id] = request.session.session_key
    context = {
        'initial_args': {
            "study-store": {
                "data": study_list
            },
            "sensor-store": {
                "data": sensors_map
            }
        }
    }
    logger.info("analytics:: study name %s", context)
    return render(request, constants.analytics_details_page, context=context)
