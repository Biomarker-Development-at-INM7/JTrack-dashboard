import logging

from django.utils import timezone

from jdash.models import Study as StudyModel
from jdash.models import SurveyPublishState

logger = logging.getLogger("django")


def get_publish_target_studies(survey_id):
    """
    Return studies linked to a survey.

    Open studies are preferred because they are the ones still visible to
    participants. If only closed studies are linked, return those so older
    records can still be published explicitly.
    """
    open_studies = list(
        StudyModel.objects.filter(survey_id=survey_id, closed=False).order_by("title", "id")
    )
    if open_studies:
        return open_studies
    return list(StudyModel.objects.filter(survey_id=survey_id).order_by("title", "id"))


def mark_survey_unpublished(survey_id):
    """
    Mark every linked study/survey pair as having unpublished DB edits.

    Returns the number of linked studies affected.
    """
    studies = get_publish_target_studies(survey_id)
    if not studies:
        logger.info("mark_survey_unpublished no linked studies for survey_id=%s", survey_id)
        return 0

    now = timezone.now()
    for study in studies:
        SurveyPublishState.objects.update_or_create(
            study=study,
            survey_id=survey_id,
            defaults={
                "has_unpublished_changes": True,
                "last_edited_at": now,
            },
        )
    logger.info(
        "mark_survey_unpublished survey_id=%s linked_study_count=%s",
        survey_id,
        len(studies),
    )
    return len(studies)


def mark_study_survey_published(study_id, survey_id):
    """Mark one study/survey pair as published."""
    now = timezone.now()
    SurveyPublishState.objects.update_or_create(
        study_id=study_id,
        survey_id=survey_id,
        defaults={
            "has_unpublished_changes": False,
            "last_published_at": now,
        },
    )


def get_survey_publish_summary(survey_id):
    """Return linked-study and unpublished-change state for a survey."""
    studies = get_publish_target_studies(survey_id)
    study_ids = [study.id for study in studies]
    states = {
        state.study_id: state
        for state in SurveyPublishState.objects.filter(
            survey_id=survey_id,
            study_id__in=study_ids,
        )
    }

    unpublished_studies = [
        study
        for study in studies
        if states.get(study.id) is not None
        and states[study.id].has_unpublished_changes
    ]
    study_names = [study.title for study in studies]
    unpublished_study_names = [study.title for study in unpublished_studies]
    study_options = []
    unpublished_study_options = []
    for study in studies:
        state = states.get(study.id)
        has_unpublished_changes = bool(state and state.has_unpublished_changes)
        has_never_been_committed = state is None
        study_option = {
            "id": study.id,
            "title": study.title,
            "is_closed": study.closed,
            "has_unpublished_changes": has_unpublished_changes,
            "has_never_been_committed": has_never_been_committed,
            "last_edited_at": state.last_edited_at if state else None,
            "last_published_at": state.last_published_at if state else None,
            "is_checked": has_unpublished_changes or has_never_been_committed,
        }
        study_options.append(study_option)
        if has_unpublished_changes or has_never_been_committed:
            unpublished_study_options.append(study_option)

    return {
        "associated_study_count": len(studies),
        "associated_study_names": study_names,
        "associated_study_label": ", ".join(study_names),
        "study_options": study_options,
        "unpublished_study_options": unpublished_study_options,
        "publish_modal_study_options": unpublished_study_options or study_options,
        "has_unpublished_changes": bool(unpublished_studies),
        "unpublished_count": len(unpublished_studies),
        "unpublished_study_names": unpublished_study_names,
        "last_edited_at": max(
            (
                state.last_edited_at
                for state in states.values()
                if state.last_edited_at is not None
            ),
            default=None,
        ),
        "last_published_at": max(
            (
                state.last_published_at
                for state in states.values()
                if state.last_published_at is not None
            ),
            default=None,
        ),
    }
