###########################################################################
####                admin.py
####           Interface to deeclare each models created 
####           Declared Models will be shown in the admin module
####           created by mnarava
####
####
###########################################################################
import sys
sys.path.append('./')
from django.contrib import admin
from django.db.models import Q

from .models import (Study, Subject, Survey, 
                     Answer, Category, Question,
                     DeviceCatalog,SensorCatalog,
                     Task,DeviceSensor,
                     StudyDeviceSensor,
                     # ResolutionCatalog,
                     SamplingRateCatalog,
                     UnitCatalog)


# ---------- Shared behavior ----------

class SearchByIdBoostMixin:
    """Boost exact numeric ID searches."""
    def get_search_results(self, request, queryset, search_term):
        qs, use_distinct = super().get_search_results(request, queryset, search_term)
        if search_term.isdigit():
            qs = queryset.filter(id=int(search_term)) | qs
        return qs, use_distinct


class JDashBaseAdmin(SearchByIdBoostMixin, admin.ModelAdmin):
    """No filters, fast list, basic QoL."""
    list_filter = ()
    ordering = ("-id",)
    list_per_page = 100
    show_full_result_count = False
    list_select_related = True      # harmless if no FKs


# ---------- Per-model admins ----------

@admin.register(Category)
class CategoryAdmin(JDashBaseAdmin):
    list_display = ("id", "categoryTitle", "survey")
    list_display_links = ("id","categoryTitle")
    search_fields = ("id", "categoryTitle","survey__title")
    search_help_text = "Search by numeric ID or categoryTitle (case-insensitive)."


@admin.register(Question)
class QuestionAdmin(JDashBaseAdmin):
    list_display = ("id", "sortId", "title", "survey")
    list_display_links = ("id", "title")
    list_editable = ("sortId",)
    search_fields = ("id", "title","survey__title")
    search_help_text = "Search by numeric ID or title (case-insensitive)."


@admin.register(Survey)
class SurveyAdmin(JDashBaseAdmin):
    # adjust 'title' if your field is named differently (e.g., 'name')
    list_display = ("id", "title",)
    list_display_links = ("id", "title")
    search_fields = ("id", "title")
    search_help_text = "Search by numeric ID or title (case-insensitive)."

class TaskInline(admin.TabularInline):   # or admin.StackedInline
    model = Task
    extra = 1
    fields = ("sortId", "task_name")
    show_change_link = True
    
class StudDeviceSensorInline(admin.TabularInline):   # or admin.StackedInline
    model = StudyDeviceSensor
    extra = 1
    fields = (
        "device_sensor",
        # Resolution support is currently disabled in the study UI/model.
        # "resolution",
        "sampling_rate",
        "unit",
        "is_enabled",
    )
    show_change_link = True

        
@admin.register(Study)
class StudyAdmin(JDashBaseAdmin):
    inlines = [TaskInline, StudDeviceSensorInline]
    list_display = ("id", "title","owner","closed")
    list_display_links = ("id", "title")
    search_fields = ("id", "title")
    search_help_text = "Search by numeric ID or title (case-insensitive)."


@admin.register(Subject)
class SubjectAdmin(JDashBaseAdmin):
    list_display = ("studyId", "username", "status")
    list_display_links = ("studyId", "username")
    list_editable = ("status",)
    search_fields = ("id", "username")
    search_help_text = "Search by numeric ID or username (case-insensitive)."

@admin.register(Answer)
class AnswerAdmin(JDashBaseAdmin):
    list_display = ("id", "answerSortId", "text","question")
    list_display_links = ("id", "text")
    list_editable = ("answerSortId",)
    search_fields = ("id", "text","question__id")
    search_help_text = "Search by numeric ID or text (case-insensitive)."
    
@admin.register(DeviceSensor)
class DeviceSensor(JDashBaseAdmin):
    list_display = ("id", "device", "sensor")
    list_display_links = ("id",)
    search_fields = ("id", "name", "label")
    search_help_text = "Search by numeric ID, device name, or sensor label (case-insensitive)."
    
@admin.register(DeviceCatalog)
class DeviceAdmin(JDashBaseAdmin):
    list_display = ("id", "name", "model")
    list_display_links = ("id", "name")
    search_fields = ("id", "name",  "model")
    search_help_text = "Search by numeric ID, name, or model (case-insensitive)."
    
@admin.register(SensorCatalog)
class SensorAdmin(JDashBaseAdmin):
    list_display = ( "code", "label")
    list_display_links = ("label","code")
    search_fields = ("label", "code")
    search_help_text = "Search by label (case-insensitive)."
    
# Resolution support is currently disabled in the study UI/model.
# @admin.register(ResolutionCatalog)
# class ResolutionCatalogAdmin(JDashBaseAdmin):
#     list_display = ("id", "value")
#     list_display_links = ("id", "value")
#     search_fields = ("id", "value")
#     search_help_text = "Search by numeric ID or value (case-insensitive)." 
    
@admin.register(SamplingRateCatalog)
class SamplingRateCatalogAdmin(JDashBaseAdmin):
    list_display = ("id", "value", "sensor")
    list_display_links = ("id", "value")
    search_fields = ("id", "value", "sensor__label", "sensor__code")
    search_help_text = "Search by numeric ID , value or sensor (case-insensitive)."

@admin.register(UnitCatalog)
class UnitCatalogAdmin(JDashBaseAdmin):
    list_display = ("id", "value", "sensor")
    list_display_links = ("id", "value")
    search_fields = ("id", "value", "sensor__label", "sensor__code")
    search_help_text = "Search by numeric ID, value, or sensor (case-insensitive)."
