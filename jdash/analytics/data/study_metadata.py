"""Analytics access to study metadata in the main storage folder."""

import json
import os

from jdash.config import constants
from jdash.config import runtime_config as config


def analytics_study_json_path(study_name):
    """Return the study JSON path from the main configured storage folder."""
    return os.path.join(
        config.studies_folder,
        study_name,
        f"{study_name}.json",
    )


def get_analytics_study_json(study_name):
    """Load and normalize Analytics study metadata from main storage."""
    with open(
        analytics_study_json_path(study_name),
        "r",
        encoding=constants.encoding,
    ) as study_file:
        data = json.load(study_file)

    data["number_of_subjects"] = data.get("number_of_subjects", 0)
    data["number-of-subjects"] = data["number_of_subjects"]
    normalized = {
        key.replace("-", "_"): value
        for key, value in data.items()
    }
    if "sensor_list" in data:
        normalized["sensor_size"] = len(data["sensor_list"]) * 2
        if "sensor_list_limited" in data:
            normalized["sensor_size"] += len(data["sensor_list_limited"]) * 2
    return normalized
