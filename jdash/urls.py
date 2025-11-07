###########################################################################
####                urls.py
####           File to include method for each service
####           created by mnarava
####
####
###########################################################################

from django.contrib import admin
from django.urls import path
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView
from . import views
from jdash.classes.analytics import dash_plot
from jdash.apps import constants as constants

urlpatterns = [
    path('favicon.ico', RedirectView.as_view(url=staticfiles_storage.url('icons/favicon.ico'))),
    path('', views.index,name=constants.url_name_for_home),
    path('login/', views.login_request , name=constants.url_name_for_login),
    path('logout/', views.logout_request , name=constants.url_name_for_logout),
    path('contactus/', views.contact_email , name=constants.url_name_for_contact_email),
    path('add/', views.add_study , name=constants.url_name_for_add_study),
    path('edit/<str:study_name>', views.edit_study , name=constants.url_name_for_edit_study),
    path('qc/<str:study_name>', views.qc_study , name=constants.url_name_for_qc_study),
    path('details/<str:study_name>', views.study_details , name=constants.url_name_for_details),
    #path('details/<str:study_name>/<str:id_type>', views.study_details , name=constants.url_name_for_details),
    path('deletesurvey/' ,views.delete_survey , name=constants.url_name_for_delete_survey ),
    path('deletequest/' ,views.create_survey , name=constants.url_name_for_delete_question ),
    path('createsurvey/' ,views.create_survey , name=constants.url_name_for_create_survey ),
    path('createsurvey/<int:survey_id>' ,views.create_survey , name=constants.url_name_for_create_survey ),
    path('createsurvey/<int:survey_id>/question/<int:question_id>' ,views.manage_question , name=constants.url_name_for_manage_question ),
    path('createsurvey/<int:survey_id>/category' ,views.manage_category_for_survey , name=constants.url_name_for_create_categories ),
    path('createsurvey/<int:survey_id>/copy' ,views.duplicate_survey , name=constants.url_name_for_duplicate_survey ),
    path('createsurvey/<int:survey_id>/copy/<int:question_id>' ,views.duplicate_question , name=constants.url_name_for_duplicate_question ),
    path('edit/<str:study_name>/editsurvey' ,views.edit_survey , name=constants.url_name_for_edit_survey ),
    path('survey/', views.survey_list , name=constants.url_name_for_survey),
    path('close/<str:study_name>', views.close , name=constants.url_name_for_close),
    path('download_dataset/<str:arg>/', views.download_dataset_from_link , name=constants.url_name_for_download_dataset),
    path('createsurvey/<int:survey_id>/download_json/', views.download_survey_json , name=constants.url_name_for_download_json),
    path('download/<str:arg>/', views.download_unused_files , name=constants.url_name_for_download),
    path('download/<str:study_name>/ics/<str:subject_id>/', views.download_calendar_for_subject , name=constants.url_name_for_download_ics),
    path('list/', views.studies_list, name=constants.url_name_for_list_of_studies),
    path('analytics/', views.analytics, name=constants.url_name_for_analytics),
    path('analytics/<str:study_name>', views.analytics, name=constants.url_name_for_analytics),
    path('delete_subject/', views.delete_subject_data , name=constants.url_name_for_delete_subject_data),
    
]
