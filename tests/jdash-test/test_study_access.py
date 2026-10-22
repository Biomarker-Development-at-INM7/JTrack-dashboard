import pytest
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied, ValidationError

from jdash.config import constants
from jdash.models import Study, StudyMembership
from jdash.services import permissions, study_access


@pytest.mark.django_db
def test_maintainer_can_manage_only_their_study():
    owner = User.objects.create_user("owner")
    maintainer = User.objects.create_user("maintainer")
    other_owner = User.objects.create_user("other-owner")
    study = Study.objects.create(title="Study_A", owner=owner)
    other_study = Study.objects.create(title="Study_B", owner=other_owner)
    StudyMembership.objects.create(
        study=study,
        user=maintainer,
        role=StudyMembership.Role.MAINTAINER,
        added_by=owner,
    )

    assert permissions.can_manage_study_access(maintainer, study)
    assert not permissions.can_manage_study_access(maintainer, other_study)


@pytest.mark.django_db
def test_study_roles_control_content_permissions_without_global_groups():
    owner = User.objects.create_user("role-owner")
    maintainer = User.objects.create_user("role-maintainer")
    investigator = User.objects.create_user("role-investigator")
    viewer = User.objects.create_user("role-viewer")
    study = Study.objects.create(title="Role_Study", owner=owner)

    StudyMembership.objects.bulk_create(
        [
            StudyMembership(study=study, user=maintainer, role=StudyMembership.Role.MAINTAINER),
            StudyMembership(study=study, user=investigator, role=StudyMembership.Role.INVESTIGATOR),
            StudyMembership(study=study, user=viewer, role=StudyMembership.Role.VIEWER),
        ]
    )

    assert permissions.can_manage_study(maintainer, study)
    assert permissions.can_manage_subjects(maintainer, study)
    assert permissions.can_manage_study(investigator, study)
    assert permissions.can_manage_subjects(investigator, study)
    assert not permissions.can_manage_study(viewer, study)
    assert not permissions.can_manage_subjects(viewer, study)
    assert permissions.can_view_study(viewer, study)
    assert permissions.can_create_study(maintainer)
    assert permissions.can_create_study(investigator)
    assert not permissions.can_create_study(viewer)


@pytest.mark.django_db
def test_default_viewer_cannot_create_a_study_until_assigned_an_editor_role():
    viewer = User.objects.create_user("default-viewer")
    viewer.groups.add(Group.objects.create(name=constants.group_name_viewer))

    assert not permissions.can_create_study(viewer)

    study_owner = User.objects.create_user("default-viewer-owner")
    study = Study.objects.create(title="Default_Viewer_Study", owner=study_owner)
    StudyMembership.objects.create(
        study=study,
        user=viewer,
        role=StudyMembership.Role.INVESTIGATOR,
    )

    assert permissions.can_create_study(viewer)


@pytest.mark.django_db
def test_investigator_cannot_manage_an_unassigned_study():
    owner = User.objects.create_user("cross-owner")
    investigator = User.objects.create_user("cross-investigator")
    assigned_study = Study.objects.create(title="Assigned_Study", owner=owner)
    other_study = Study.objects.create(title="Other_Study", owner=owner)
    StudyMembership.objects.create(
        study=assigned_study,
        user=investigator,
        role=StudyMembership.Role.INVESTIGATOR,
    )

    assert permissions.can_manage_study(investigator, assigned_study)
    assert not permissions.can_manage_study(investigator, other_study)
    assert not permissions.can_view_study(investigator, other_study)


@pytest.mark.django_db
def test_study_owner_without_membership_has_no_study_permissions():
    owner = User.objects.create_user("owner-without-membership")
    study = Study.objects.create(title="Membership_Only_Study", owner=owner)

    assert not permissions.can_view_study(owner, study)
    assert not permissions.can_manage_study(owner, study)
    assert not permissions.can_manage_study_access(owner, study)
    assert permissions.can_create_study(owner)


@pytest.mark.django_db
def test_legacy_global_investigator_group_does_not_grant_study_access():
    user = User.objects.create_user("legacy-global-investigator")
    owner = User.objects.create_user("study-owner")
    study = Study.objects.create(title="Membership_Only_Global_Group", owner=owner)
    user.groups.add(Group.objects.create(name=constants.group_name_investigator))

    assert not permissions.can_view_study(user, study)
    assert not permissions.can_manage_study(user, study)
    assert not permissions.can_manage_study_access(user, study)


@pytest.mark.django_db
def test_principal_investigator_controls_conclusion_and_owner_qc_checks():
    owner = User.objects.create_user("qc-owner")
    principal_investigator = User.objects.create_user("principal-investigator")
    investigator = User.objects.create_user("qc-investigator")
    study = Study.objects.create(title="QC_Roles_Study", owner=owner)
    StudyMembership.objects.bulk_create(
        [
            StudyMembership(
                study=study,
                user=principal_investigator,
                role=StudyMembership.Role.MAINTAINER,
            ),
            StudyMembership(
                study=study,
                user=investigator,
                role=StudyMembership.Role.INVESTIGATOR,
            ),
        ]
    )

    assert permissions.can_conclude_study(principal_investigator, study)
    assert permissions.can_update_qc_owner_checks(principal_investigator, study)
    assert not permissions.can_update_qc_admin_checks(principal_investigator, study)
    assert not permissions.can_conclude_study(investigator, study)
    assert not permissions.can_update_qc_owner_checks(investigator, study)
    assert not permissions.can_update_qc_admin_checks(investigator, study)


@pytest.mark.django_db
def test_investigator_can_manage_survey_linked_to_assigned_study():
    from jdash.models import Survey

    owner = User.objects.create_user("survey-owner")
    investigator = User.objects.create_user("survey-investigator")
    survey = Survey.objects.create(title="Assigned Survey", description="", owner=owner)
    other_survey = Survey.objects.create(title="Other Survey", description="", owner=owner)
    study = Study.objects.create(title="Survey_Study", owner=owner, survey=survey)
    StudyMembership.objects.create(
        study=study,
        user=investigator,
        role=StudyMembership.Role.INVESTIGATOR,
    )

    assert permissions.can_manage_survey(investigator, survey)
    assert permissions.can_manage_questions(investigator, survey)
    assert permissions.can_view_survey(investigator, survey)
    assert not permissions.can_manage_survey(investigator, other_survey)
    assert not permissions.can_view_survey(investigator, other_survey)


@pytest.mark.django_db
def test_linked_study_owner_without_membership_has_no_survey_permissions():
    from jdash.models import Survey

    owner = User.objects.create_user("linked-survey-owner")
    survey = Survey.objects.create(title="Linked survey", description="", owner=owner)
    Study.objects.create(title="Linked_Survey_Study", owner=owner, survey=survey)

    assert not permissions.can_manage_survey(owner, survey)
    assert not permissions.can_view_survey(owner, survey)


@pytest.mark.django_db
def test_maintainer_can_add_investigator_membership():
    owner = User.objects.create_user("owner")
    maintainer = User.objects.create_user("maintainer")
    investigator = User.objects.create_user("investigator")
    study = Study.objects.create(title="Study_A", owner=owner)
    StudyMembership.objects.create(
        study=study,
        user=maintainer,
        role=StudyMembership.Role.MAINTAINER,
        added_by=owner,
    )

    membership = study_access.add_membership(
        maintainer,
        study.pk,
        investigator.pk,
        StudyMembership.Role.INVESTIGATOR,
    )

    assert membership.role == StudyMembership.Role.INVESTIGATOR


@pytest.mark.django_db
def test_username_search_rejects_unknown_user():
    owner = User.objects.create_user("owner")
    study = Study.objects.create(title="Study_A", owner=owner)
    StudyMembership.objects.create(
        study=study,
        user=owner,
        role=StudyMembership.Role.MAINTAINER,
        added_by=owner,
    )

    with pytest.raises(ValidationError, match="No user exists with that username"):
        study_access.add_membership_by_username(
            owner,
            study.pk,
            "missing-user",
            StudyMembership.Role.VIEWER,
        )


@pytest.mark.django_db
def test_only_administrator_can_assign_maintainer():
    owner = User.objects.create_user("owner")
    new_member = User.objects.create_user("new-member")
    study = Study.objects.create(title="Study_A", owner=owner)
    StudyMembership.objects.create(
        study=study,
        user=owner,
        role=StudyMembership.Role.MAINTAINER,
        added_by=owner,
    )

    with pytest.raises(PermissionDenied):
        study_access.add_membership(
            owner,
            study.pk,
            new_member.pk,
            StudyMembership.Role.MAINTAINER,
        )

    admin_group = Group.objects.create(name=constants.group_name_administrator)
    owner.groups.add(admin_group)
    membership = study_access.add_membership(
        owner,
        study.pk,
        new_member.pk,
        StudyMembership.Role.MAINTAINER,
    )
    assert membership.role == StudyMembership.Role.MAINTAINER


@pytest.mark.django_db
def test_owner_cannot_be_removed_or_demoted():
    owner = User.objects.create_user("owner")
    study = Study.objects.create(title="Study_A", owner=owner)
    membership = StudyMembership.objects.create(
        study=study,
        user=owner,
        role=StudyMembership.Role.MAINTAINER,
        added_by=owner,
    )

    with pytest.raises(ValidationError):
        study_access.update_membership(
            owner,
            study.pk,
            membership.pk,
            StudyMembership.Role.VIEWER,
        )
    with pytest.raises(ValidationError):
        study_access.remove_membership(owner, study.pk, membership.pk)
