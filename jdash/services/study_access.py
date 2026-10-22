"""Study-scoped membership and role management."""

import logging

from auditlog.models import LogEntry
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, transaction

from jdash.models import Study, StudyMembership
from jdash.repositories.study_repository import log_action
from jdash.services import permissions


logger = logging.getLogger("django")


def _log_membership_action(actor, study, message):
    """Write access audit history without blocking the membership operation."""
    try:
        with transaction.atomic():
            log_action(actor, study, LogEntry.Action.UPDATE, message)
    except DatabaseError:
        logger.exception(
            "Could not write study-access audit entry for study %s",
            study.pk,
        )


def manageable_studies(user):
    """Return studies whose access list the user may administer."""
    queryset = Study.objects.filter(closed=False)
    if permissions.is_administrator(user):
        return queryset.order_by("title")
    return queryset.filter(
        memberships__user=user,
        memberships__role=StudyMembership.Role.MAINTAINER,
    ).distinct().order_by("title")


def membership_context(user, requested_study_id=None):
    studies = manageable_studies(user)
    selected_study = None
    if requested_study_id:
        selected_study = studies.filter(pk=requested_study_id).first()
    if selected_study is None:
        selected_study = studies.first()

    memberships = StudyMembership.objects.none()
    if selected_study:
        memberships = selected_study.memberships.select_related("user", "added_by")

    roles = [
        (StudyMembership.Role.INVESTIGATOR, StudyMembership.Role.INVESTIGATOR.label),
        (StudyMembership.Role.VIEWER, StudyMembership.Role.VIEWER.label),
    ]
    if permissions.is_administrator(user):
        roles.insert(0, (StudyMembership.Role.MAINTAINER, "Principal Investigator"))

    return {
        "managed_studies": studies,
        "selected_study": selected_study,
        "study_memberships": memberships,
        "assignable_roles": roles,
        "can_assign_maintainer": permissions.is_administrator(user),
    }


def _study_for_actor(actor, study_id):
    try:
        study = Study.objects.filter(pk=study_id, closed=False).first()
    except (TypeError, ValueError):
        study = None
    if study is None or not permissions.can_manage_study_access(actor, study):
        raise PermissionDenied("You cannot manage access for this study.")
    return study


def _validate_role(actor, role):
    valid_roles = {choice.value for choice in StudyMembership.Role}
    if role not in valid_roles:
        raise ValidationError("Select a valid study role.")
    if role == StudyMembership.Role.MAINTAINER and not permissions.is_administrator(actor):
        raise PermissionDenied("Only administrators can assign the Principal Investigator role.")


@transaction.atomic
def add_membership(actor, study_id, user_id, role):
    study = _study_for_actor(actor, study_id)
    _validate_role(actor, role)
    try:
        member = User.objects.filter(pk=user_id, is_active=True).first()
    except (TypeError, ValueError):
        member = None
    if member is None:
        raise ValidationError("Select an active registered user.")
    if StudyMembership.objects.filter(study=study, user=member).exists():
        raise ValidationError("This user is already assigned to the study.")

    membership = StudyMembership.objects.create(
        study=study,
        user=member,
        role=role,
        added_by=actor,
    )
    _log_membership_action(
        actor,
        study,
        f"Added {member.username} as {membership.get_role_display()}.",
    )
    return membership


def add_membership_by_username(actor, study_id, username, role):
    """Add an active registered user resolved by an exact username search."""
    normalized_username = str(username or "").strip()
    if not normalized_username:
        raise ValidationError("Enter a username.")
    member = User.objects.filter(
        username__iexact=normalized_username,
        is_active=True,
    ).first()
    if member is None:
        raise ValidationError("No user exists with that username.")
    return add_membership(actor, study_id, member.pk, role)


@transaction.atomic
def update_membership(actor, study_id, membership_id, role):
    study = _study_for_actor(actor, study_id)
    _validate_role(actor, role)
    try:
        membership = study.memberships.select_related("user").filter(pk=membership_id).first()
    except (TypeError, ValueError):
        membership = None
    if membership is None:
        raise ValidationError("The selected study member no longer exists.")
    if membership.role == StudyMembership.Role.MAINTAINER and not permissions.is_administrator(actor):
        raise PermissionDenied("Only administrators can change a Principal Investigator membership.")
    if membership.user_id == study.owner_id and role != StudyMembership.Role.MAINTAINER:
        raise ValidationError("The study owner must remain a Principal Investigator.")
    if (
        membership.role == StudyMembership.Role.MAINTAINER
        and role != StudyMembership.Role.MAINTAINER
        and study.memberships.filter(role=StudyMembership.Role.MAINTAINER).count() <= 1
    ):
        raise ValidationError("A study must have at least one Principal Investigator.")

    previous_role = membership.get_role_display()
    membership.role = role
    membership.save(update_fields=["role", "updated_at"])
    _log_membership_action(
        actor,
        study,
        f"Changed {membership.user.username} from {previous_role} to {membership.get_role_display()}.",
    )
    return membership


@transaction.atomic
def remove_membership(actor, study_id, membership_id):
    study = _study_for_actor(actor, study_id)
    try:
        membership = study.memberships.select_related("user").filter(pk=membership_id).first()
    except (TypeError, ValueError):
        membership = None
    if membership is None:
        raise ValidationError("The selected study member no longer exists.")
    if membership.role == StudyMembership.Role.MAINTAINER and not permissions.is_administrator(actor):
        raise PermissionDenied("Only administrators can remove a Principal Investigator membership.")
    if membership.user_id == study.owner_id:
        raise ValidationError("The study owner cannot be removed.")
    if (
        membership.role == StudyMembership.Role.MAINTAINER
        and study.memberships.filter(role=StudyMembership.Role.MAINTAINER).count() <= 1
    ):
        raise ValidationError("A study must have at least one Principal Investigator.")

    username = membership.user.username
    membership.delete()
    _log_membership_action(
        actor,
        study,
        f"Removed {username} from the study access list.",
    )
