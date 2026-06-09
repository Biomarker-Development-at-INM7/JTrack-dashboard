from django.utils.translation import gettext_lazy as _

class TextMessages:
    """
    This class stores stable translation keys for backend messages and help texts.

    The attributes are intentionally translation ids instead of full English
    sentences so the actual text lives in the Django ``.po`` files.
    """

    message_type_not_found = _("text_message_type_not_found")

    def get_message(self, message_type):
        try:
            return getattr(self, message_type)
        except AttributeError:
            return self.message_type_not_found

    def customize_message(self, message_type, **kwargs):
        message_template = self.get_message(message_type)
        if message_template == self.message_type_not_found:
            return message_template
        return message_template.format(**kwargs)

    # Success messages
    success_contacting_message = _("text_success_contacting_message")
    success_deletion_data_request = _("text_success_deletion_data_request")
    success_new_user = _("text_success_new_user")
    success_notification = _("text_success_notification")
    success_study_updated = _("text_success_study_updated")
    success_logged_out = _("text_success_logged_out")

    # Error messages
    error_message_to_contact_support = _("text_error_message_to_contact_support")
    error_message_invalid_username_pswd = _("text_error_message_invalid_username_pswd")

    # Informational texts
    info_text_ema = _("text_info_ema")
    info_text_passive_monitoring = _("text_info_passive_monitoring")
    info_text_no_labelling = _("text_info_no_labelling")
    info_text_active_labelling = _("text_info_active_labelling")
    info_text_manual_active_labelling = _("text_info_manual_active_labelling")
    info_text_partial_active_labelling = _("text_info_partial_active_labelling")

    # Help texts for studies
    help_text_study_title = _("text_help_study_title")
    help_text_study_description = _("text_help_study_description")
    help_text_study_isTest = _("text_help_study_is_test")
    help_text_study_duration = _("text_help_study_duration")
    help_text_study_numberOfSubjects = _("text_help_study_number_of_subjects")
    help_text_study_passiveSensors = _("text_help_study_passive_sensors")
    help_text_study_activeSensors = _("text_help_study_active_sensors")
    help_text_study_frequency = _("text_help_study_frequency")
    help_text_study_ema = _("text_help_study_ema")
    help_text_study_select_ema = _("text_help_study_select_ema")
    help_text_study_upload_ema_json = _("text_help_study_upload_ema_json")
    help_text_study_upload_ema_images = _("text_help_study_upload_ema_images")
    help_text_study_task_title = _("text_help_study_task_title")
    help_text_study_task_description = _("text_help_study_task_description")
    help_text_study_task_preparation = _("text_help_study_task_preparation")
    help_text_study_task_duration = _("text_help_study_task_duration")

    # Help texts for surveys
    help_text_survey_title = _("text_help_survey_title")
    help_text_survey_description = _("text_help_survey_description")
    help_text_survey_splitByCategory = _("text_help_survey_split_by_category")
    help_text_survey_scrolling = _("text_help_survey_scrolling")
    help_text_survey_topN = _("text_help_survey_top_n")
    help_text_survey_question_sortId = _("text_help_survey_question_sort_id")
    help_text_survey_question_title = _("text_help_survey_question_title")
    help_text_survey_question_description = _("text_help_survey_question_description")
    help_text_survey_question_type = _("text_help_survey_question_type")
    help_text_survey_question_category = _("text_help_survey_question_category")
    help_text_survey_question_firstDayToAnswer = _("text_help_survey_question_first_day_to_answer")
    help_text_survey_question_imageURL = _("text_help_survey_question_image_url")
    help_text_survey_question_url = _("text_help_survey_question_url")
    help_text_survey_question_frequency = _("text_help_survey_question_frequency")
    help_text_survey_question_clockTime = _("text_help_survey_question_clock_time")
    help_text_survey_question_clockTime_start = _("text_help_survey_question_clock_time_start")
    help_text_survey_question_clockTime_end = _("text_help_survey_question_clock_time_end")
    help_text_survey_category_activate_question = _("text_help_survey_category_activate_question")
    help_text_survey_category_deactivate_question = _("text_help_survey_category_deactivate_question")
    help_text_survey_category_activation_condition = _("text_help_survey_category_activation_condition")
    help_text_survey_category_deactivation_condition = _("text_help_survey_category_deactivation_condition")
    help_text_survey_question_deactivateOnAnswer = _("text_help_survey_question_deactivate_on_answer")
    help_text_survey_question_deactivateOnDate = _("text_help_survey_question_deactivate_on_date")
    help_text_survey_question_answerForm = _("text_help_survey_question_answer_form")

    help_text_survey_category_title = _("text_help_survey_category_title")
    help_text_survey_category_value = _("text_help_survey_category_value")
    help_text_survey_category_didSubjectAsk = _("text_help_survey_category_did_subject_ask")
