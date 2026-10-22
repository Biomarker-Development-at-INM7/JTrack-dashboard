from jdash.config import constants


STUDY_EDITOR_ROLES = {"maintainer", "investigator"}


def _user_group_names(user):
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    return set(user.groups.values_list("name", flat=True))


def has_any_group(user, group_names):
    return bool(_user_group_names(user).intersection(group_names))


def is_administrator(user):
    return has_any_group(user, {constants.group_name_administrator})


def highest_study_role(user):
    """Return the highest dashboard role assigned across the user's studies."""
    if not user or not getattr(user, "is_authenticated", False):
        return None
    roles = set(user.study_memberships.values_list("role", flat=True))
    for role in ("maintainer", "investigator", "viewer"):
        if role in roles:
            return role
    return None


def _study_membership_role(user, study):
    """Return the user's role for a Study instance, primary key, or title."""
    if not user or not getattr(user, "is_authenticated", False) or study is None:
        return None

    from jdash.models import StudyMembership

    memberships = StudyMembership.objects.filter(user=user)
    if hasattr(study, "pk"):
        memberships = memberships.filter(study_id=study.pk)
    elif isinstance(study, int) or (isinstance(study, str) and study.isdigit()):
        memberships = memberships.filter(study_id=int(study))
    else:
        memberships = memberships.filter(study__title=str(study))
    return memberships.values_list("role", flat=True).first()


def study_membership_role(user, study):
    """Return the user's role for one study, if they have a membership."""
    return _study_membership_role(user, study)


def is_study_principal_investigator(user, study):
    """Return whether the user has a Principal Investigator membership."""
    if not user or not getattr(user, "is_authenticated", False) or study is None:
        return False
    return _study_membership_role(user, study) == "maintainer"


def can_view_study(user, study):
    return is_administrator(user) or _study_membership_role(user, study) is not None


def can_manage_study(user, study=None):
    """Allow study edits through an Administrator role or study membership."""
    if is_administrator(user):
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if study is not None:
        return _study_membership_role(user, study) in STUDY_EDITOR_ROLES

    return user.study_memberships.filter(role__in=STUDY_EDITOR_ROLES).exists()


def can_create_study(user):
    """Any authenticated user may create a study and become its PI."""
    return bool(user and getattr(user, "is_authenticated", False))


def can_manage_study_access(user, study):
    """Return whether a user may administer memberships for one study."""
    if not user or not getattr(user, "is_authenticated", False) or study is None:
        return False
    if is_administrator(user):
        return True
    return study.memberships.filter(user=user, role="maintainer").exists()


def can_qc_study(user, study=None):
    return can_manage_study(user, study)


def can_update_qc_admin_checks(user, study):
    """Only global Administrators can complete administrator QC checks."""
    del study
    return is_administrator(user)


def can_update_qc_owner_checks(user, study):
    """Only Principal Investigators and Administrators can complete owner QC checks."""
    return can_manage_study_access(user, study)


def can_conclude_study(user, study):
    """Only administrators and Principal Investigators can conclude a study."""
    return can_manage_study_access(user, study)


def can_manage_subjects(user, study=None):
    return can_manage_study(user, study)


def can_manage_survey(user, survey=None):
    """Authorize a Survey, or a Study containing a legacy embedded survey."""
    if is_administrator(user):
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if survey is None:
        return user.study_memberships.filter(role__in=STUDY_EDITOR_ROLES).exists()

    from jdash.models import Study, Survey

    if isinstance(survey, Study):
        return can_manage_study(user, survey)
    if not isinstance(survey, Survey):
        try:
            survey = Survey.objects.get(pk=survey)
        except (Survey.DoesNotExist, TypeError, ValueError):
            return False
    linked_studies = survey.study_set.all()
    if linked_studies.exists():
        return linked_studies.filter(
            closed=False,
            memberships__user=user,
            memberships__role__in=STUDY_EDITOR_ROLES,
        ).exists()
    return survey.owner_id == user.pk


def can_view_survey(user, survey):
    """Allow access to a survey owned by or linked to a visible study."""
    if is_administrator(user):
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False

    from jdash.models import Survey

    if not isinstance(survey, Survey):
        try:
            survey = Survey.objects.get(pk=survey)
        except (Survey.DoesNotExist, TypeError, ValueError):
            return False
    linked_studies = survey.study_set.all()
    if linked_studies.exists():
        return linked_studies.filter(closed=False, memberships__user=user).exists()
    return survey.owner_id == user.pk


def can_manage_categories(user, survey=None):
    return can_manage_survey(user, survey)


def can_manage_questions(user, survey=None):
    return can_manage_survey(user, survey)


def can_duplicate_survey(user, survey=None):
    return can_manage_survey(user, survey)


def can_delete_survey(user, survey=None):
    return can_manage_survey(user, survey)
