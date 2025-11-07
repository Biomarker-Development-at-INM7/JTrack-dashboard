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

from .models import Study, Subject, Survey, Answer, Category, Question


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


@admin.register(Study)
class StudyAdmin(JDashBaseAdmin):
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


