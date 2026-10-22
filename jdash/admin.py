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
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group, User
from django import forms

from jdash.config import constants
from .models import (Study, Subject, Survey, 
                     Answer, Category, Question,
                     DeviceCatalog,SensorCatalog,
                     Task,DeviceSensor,
                     SurveyPublishState,
                     StudyMembership,
                     StudyDeviceSensor,
                     SamplingRateCatalog,
                     UnitCatalog)


LEGACY_ROLE_GROUP_NAMES = (
    constants.group_name_investigator,
    constants.group_name_viewer,
)

class JDashUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "groups" in self.fields:
            self.fields["groups"].queryset = Group.objects.exclude(name__in=LEGACY_ROLE_GROUP_NAMES)
            self.fields["groups"].label = "Global groups"
            self.fields["groups"].help_text = (
                "Only the Administrator group grants dashboard-wide access. "
                "Assign study roles from the study access page."
            )


class JDashUserAdmin(UserAdmin):
    form = JDashUserChangeForm


admin.site.unregister(User)
admin.site.register(User, JDashUserAdmin)


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


class DeviceSensorAdminForm(forms.ModelForm):
    class Meta:
        model = DeviceSensor
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        sensor_id = None
        if self.is_bound:
            sensor_id = self.data.get("sensor") or None
        elif self.instance and self.instance.pk:
            sensor_id = self.instance.sensor_id
        else:
            sensor_id = self.initial.get("sensor") or None

        if sensor_id:
            self.fields["default_sampling_rate"].queryset = SamplingRateCatalog.objects.filter(sensor_id=sensor_id)
            self.fields["default_unit"].queryset = UnitCatalog.objects.filter(sensor_id=sensor_id)
        else:
            self.fields["default_sampling_rate"].queryset = SamplingRateCatalog.objects.all()
            self.fields["default_unit"].queryset = UnitCatalog.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        sensor = cleaned_data.get("sensor")
        default_sampling_rate = cleaned_data.get("default_sampling_rate")
        default_unit = cleaned_data.get("default_unit")

        if sensor and default_sampling_rate and default_sampling_rate.sensor_id != sensor.id:
            self.add_error("default_sampling_rate", "Sampling rate must belong to the selected sensor.")

        if sensor and default_unit and default_unit.sensor_id != sensor.id:
            self.add_error("default_unit", "Unit must belong to the selected sensor.")

        return cleaned_data


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

@admin.register(SurveyPublishState)
class SurveyPublishStateAdmin(JDashBaseAdmin):
    list_display = (
        "id",
        "study",
        "survey",
        "has_unpublished_changes",
        "last_edited_at",
        "last_published_at",
    )
    list_display_links = ("id", "study")
    search_fields = ("id", "study__title", "survey__title")
    search_help_text = "Search by numeric ID, study title, or survey title."

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


class StudyMembershipInline(admin.TabularInline):
    model = StudyMembership
    extra = 0
    fields = ("user", "role", "added_by", "created_at")
    readonly_fields = ("created_at",)

        
@admin.register(Study)
class StudyAdmin(JDashBaseAdmin):
    inlines = [TaskInline, StudDeviceSensorInline, StudyMembershipInline]
    list_display = ("id", "title", "owner", "data_collection_completed", "closed")
    list_display_links = ("id", "title")
    list_filter = ("data_collection_completed", "closed")
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
class DeviceSensorAdmin(JDashBaseAdmin):
    form = DeviceSensorAdminForm
    list_display = ("id", "device", "sensor", "default_sampling_rate", "default_unit")
    list_display_links = ("id",)
    search_fields = ("id", "device__name", "sensor__label",  "default_sampling_rate__value", "default_unit__value")
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

