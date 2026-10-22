import copy
import logging

from jdash.config import constants
from jdash.services.survey_publish_state import (
    get_publish_target_studies,
    mark_study_survey_published,
)
from jdash.utils.fileutils import (
    _next_study_json_version,
    create_backup_json_file,
    open_study_json,
    save_study_json,
)

logger = logging.getLogger("django")


def publish_survey_to_linked_studies(survey_id):
    """
    Publish the latest DB-backed survey JSON into every linked study JSON.

    The DB remains the editing source of truth. Publishing creates the versioned
    study JSON snapshot that participant-facing clients read.
    """
    logger.info("publish_survey_to_linked_studies called for survey_id=%s", survey_id)
    return publish_survey_to_selected_studies(survey_id)


def publish_survey_to_selected_studies(survey_id, study_ids=None):
    """
    Publish the latest DB-backed survey JSON into selected linked study JSON files.
    """
    from jdash.services.survey import Survey

    logger.info(
        "publish_survey_to_selected_studies called for survey_id=%s selected_count=%s",
        survey_id,
        len(study_ids) if study_ids is not None else "all",
    )
    logger.debug(
        "publish_survey_to_selected_studies study_ids=%s",
        study_ids,
    )
    studies = get_publish_target_studies(survey_id)
    if not studies:
        logger.info("publish_survey_to_selected_studies no linked study for survey_id=%s", survey_id)
        return {
            "published": False,
            "published_count": 0,
            "study_names": [],
            "failed": [],
            "reason": "not_associated",
        }

    if study_ids is not None:
        selected_study_ids = set()
        for study_id in study_ids:
            try:
                selected_study_ids.add(int(study_id))
            except (TypeError, ValueError):
                continue
        studies = [study for study in studies if study.id in selected_study_ids]
        if not studies:
            logger.info(
                "publish_survey_to_selected_studies no selected linked studies for survey_id=%s",
                survey_id,
            )
            return {
                "published": False,
                "published_count": 0,
                "study_names": [],
                "failed": [],
                "reason": "no_selection",
            }

    survey_json = Survey.generate_json_for_download(survey_id)
    published_study_names = []
    failed = []

    for study in studies:
        try:
            study_json = open_study_json(study.title)
            published_json = copy.deepcopy(study_json)
            published_json[constants.key_name_survey] = copy.deepcopy(survey_json)
            create_backup_json_file(study.title, copy.deepcopy(study_json))
            published_json[constants.key_name_version] = _next_study_json_version(study_json)
            save_study_json(study.title, published_json)
            mark_study_survey_published(study.id, survey_id)
            published_study_names.append(study.title)
        except Exception as exc:
            logger.exception(
                "publish_survey_to_selected_studies failed for survey_id=%s study=%s",
                survey_id,
                study.title,
            )
            failed.append({"study_name": study.title, "error": str(exc)})

    logger.info(
        "publish_survey_to_selected_studies finished for survey_id=%s published_count=%s failed_count=%s",
        survey_id,
        len(published_study_names),
        len(failed),
    )
    return {
        "published": bool(published_study_names),
        "published_count": len(published_study_names),
        "study_names": published_study_names,
        "failed": failed,
        "reason": "" if published_study_names else "failed",
    }

