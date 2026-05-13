from auditlog.registry import auditlog

from jdash.models import (
    Answer,
    Category,
    Question,
    Study,
    StudyDeviceSensor,
    Subject,
    Survey,
    Task,
)


REGISTERED_MODELS = (
    Study,
    Survey,
    Question,
    Answer,
    Subject,
    Category,
    Task,
    StudyDeviceSensor,
)


for model in REGISTERED_MODELS:
    auditlog.register(model)
