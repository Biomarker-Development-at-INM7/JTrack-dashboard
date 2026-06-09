from jdash.config import constants


MANAGER_GROUPS = {
    constants.group_name_administrator,
    constants.group_name_investigator,
}


def _user_group_names(user):
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    return set(user.groups.values_list("name", flat=True))


def has_any_group(user, group_names):
    return bool(_user_group_names(user).intersection(group_names))


def is_administrator(user):
    return has_any_group(user, {constants.group_name_administrator})


def is_investigator(user):
    return has_any_group(user, {constants.group_name_investigator})


def is_viewer(user):
    return has_any_group(user, {constants.group_name_viewer})


def can_manage_study(user):
    return has_any_group(user, MANAGER_GROUPS)


def can_qc_study(user):
    return can_manage_study(user)


def can_manage_subjects(user):
    return can_manage_study(user)


def can_manage_survey(user):
    return has_any_group(user, MANAGER_GROUPS)


def can_manage_categories(user):
    return can_manage_survey(user)


def can_manage_questions(user):
    return can_manage_survey(user)


def can_duplicate_survey(user):
    return can_manage_survey(user)


def can_delete_survey(user):
    return can_manage_survey(user)

