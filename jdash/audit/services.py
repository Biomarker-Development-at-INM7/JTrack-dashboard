from dataclasses import dataclass
import re
from typing import Optional

from auditlog.models import LogEntry

from jdash.models import (
    Answer,
    Category,
    DeviceSensor,
    Question,
    # ResolutionCatalog,
    SamplingRateCatalog,
    Study,
    StudyDeviceSensor,
    Survey,
    Task,
    UnitCatalog,
)


@dataclass(frozen=True)
class AuditHistoryEntry:
    timestamp: object
    action: int
    action_label: str
    content_type: str
    object_repr: str
    changes: Optional[dict]
    actor: object
    log_entry: LogEntry


class AuditLogService:
    ACTION_LABELS = {
        LogEntry.Action.CREATE: "create",
        LogEntry.Action.UPDATE: "update",
        LogEntry.Action.DELETE: "delete",
        LogEntry.Action.ACCESS: "access",
    }

    @staticmethod
    def get_logs_for_instance(instance):
        return LogEntry.objects.get_for_object(instance)

    @staticmethod
    def get_logs_for_queryset(queryset):
        return LogEntry.objects.get_for_objects(queryset)

    @staticmethod
    def get_action_label(action):
        return AuditLogService.ACTION_LABELS.get(action, str(action))

    @staticmethod
    def clean_object_repr(object_repr):
        if not object_repr:
            return object_repr

        cleaned = re.sub(r"\s*object\s*\(\d+\)\s*$", "", str(object_repr), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*\bdb_id\b\s*[:=]?\s*\d+\b", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip(" ,;-")
        return cleaned or str(object_repr)

class StudyAuditService:
    """
    Build a merged study audit timeline from the raw per-model audit entries.
    This keeps write-path code clean while still allowing a single HTML history
    view for a study and its directly owned child records.
    """

    @staticmethod
    def get_related_querysets(study: Study):
        return {
            "tasks": Task.objects.filter(study=study),
            "study_device_sensors": StudyDeviceSensor.objects.filter(study=study),
        }

    @staticmethod
    def get_history(study: Study):
        logs = list(AuditLogService.get_logs_for_instance(study))

        for queryset in StudyAuditService.get_related_querysets(study).values():
            if not queryset.exists():
                continue
            logs.extend(AuditLogService.get_logs_for_queryset(queryset))

        logs.sort(key=lambda entry: entry.timestamp, reverse=True)
        return [StudyAuditService._to_history_entry(entry) for entry in logs]

    @staticmethod
    def _to_history_entry(entry: LogEntry):
        changes = entry.changes
        if entry.content_type.model == "studydevicesensor":
            changes = StudyAuditService._format_study_device_sensor_changes(entry.changes)

        return AuditHistoryEntry(
            timestamp=entry.timestamp,
            action=entry.action,
            action_label=AuditLogService.get_action_label(entry.action),
            content_type=entry.content_type.model,
            object_repr=AuditLogService.clean_object_repr(entry.object_repr),
            changes=changes,
            actor=entry.actor,
            log_entry=entry,
        )

    @staticmethod
    def _format_study_device_sensor_changes(changes):
        if not changes:
            return changes

        fk_models = {
            "device_sensor": DeviceSensor,
            # Resolution support is currently disabled in the study UI/model.
            # "resolution": ResolutionCatalog,
            "sampling_rate": SamplingRateCatalog,
            "unit": UnitCatalog,
        }

        formatted_changes = dict(changes)
        for field, model in fk_models.items():
            if field not in formatted_changes:
                continue

            old_value, new_value = formatted_changes[field]
            formatted_changes[field] = [
                StudyAuditService._format_fk_change_value(model, old_value),
                StudyAuditService._format_fk_change_value(model, new_value),
            ]

        return formatted_changes

    @staticmethod
    def _format_fk_change_value(model, value):
        if value in (None, "", "None"):
            return "-"

        try:
            pk = int(value)
        except (TypeError, ValueError):
            return str(value)

        obj = model.objects.filter(pk=pk).first()
        if obj is None:
            return str(pk)

        label = getattr(obj, "value", None) or str(obj)
        return f"{pk} | {label}"


class SurveyAuditService:
    """
    Build a merged survey audit timeline from the raw per-model audit entries.
    Includes the survey plus its questions, answers, and categories.
    """

    @staticmethod
    def get_related_querysets(survey: Survey):
        questions = Question.objects.filter(survey=survey)
        return {
            "questions": questions,
            "answers": Answer.objects.filter(question__survey=survey),
            "categories": Category.objects.filter(survey=survey),
        }

    @staticmethod
    def get_history(survey: Survey):
        logs = list(AuditLogService.get_logs_for_instance(survey))

        for queryset in SurveyAuditService.get_related_querysets(survey).values():
            if not queryset.exists():
                continue
            logs.extend(AuditLogService.get_logs_for_queryset(queryset))

        logs.sort(key=lambda entry: entry.timestamp, reverse=True)
        return [SurveyAuditService._to_history_entry(entry) for entry in logs]

    @staticmethod
    def _to_history_entry(entry: LogEntry):
        changes = entry.changes
        return AuditHistoryEntry(
            timestamp=entry.timestamp,
            action=entry.action,
            action_label=AuditLogService.get_action_label(entry.action),
            content_type=entry.content_type.model,
            object_repr=AuditLogService.clean_object_repr(entry.object_repr),
            changes=changes,
            actor=entry.actor,
            log_entry=entry,
        )

