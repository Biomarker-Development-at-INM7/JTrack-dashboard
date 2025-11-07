"""
Classes:
    TextMessages - Stores and manages predefined message templates.
"""
class TextMessages:
    """
    This class stores standard message templates for various user interactions.
    """
    def get_message(self, message_type):
        """
        Retrieves a message template based on the specified type.
        
        Args:
        message_type (str): The key corresponding to the message template.
        
        Returns:
        str: The message template if found, else an error message.
        """
        try:
            return getattr(self, message_type)
        except AttributeError:
            return "Message type not found."
            
        
    def customize_message(self, message_type, **kwargs):
        """
        Customizes a message template with provided keyword arguments.
        
        Args:
        message_type (str): The key corresponding to the message template to be customized.
        **kwargs (dict): Keyword arguments that correspond to placeholders in the message template.
        
        Returns:
        str: Customized message or an error if the message type is not found.
        """
        message_template = self.get_message(message_type)
        if "Message type not found." in message_template:
            return message_template
        return message_template.format(**kwargs)
        
    # Success messages
    success_contacting_message = (
        "Thank you for reaching out to collaborate with us. While our team is looking over your message, "
        "get ready for what we'll do next. We'll be in touch faster than you can say 'innovation explosion'!"
    )
    
    success_deletion_data_request = (
        "Your request for data deletion is on its way to our digital shredder. Remember, once it's gone, "
        "it's like it never existed. Give us a bit to sprinkle the magic dust, and soon, your request will be "
        "nothing but a vanishing act in our logs. 🐇💨"
    )
    
    success_new_user = "New users have been successfully created."
    success_notification = "Notification has been sent successfully."
    success_study_updated = "Study has been successfully updated."
    
    # Informational texts
    info_text_ema = (
        "This study uses the EMA application, and the assessment and resources should be uploaded "
        "during the creation of the study."
    )
    
    info_text_passive_monitoring = (
        "In this mode, selected sensors will continue to record data in the background without further interaction "
        "from users. Please note that the selected frequency will only apply to accelerometer and gyroscope sensors. "
        "Other sensors will have their own pre-defined frequency (unchangeable)."
    )
    
    info_text_no_labelling = (
        "This is a default for passive monitoring and passively recorded data will not be labeled. "
        "(The task button will be deactivated in the app if selected.)"
    )
    
    info_text_active_labelling = (
        "There will be a pre-defined task that the user should perform in the application. "
        "The selected sensor will only record during the task."
    )
    
    info_text_manual_active_labelling = (
        'This mode is similar to "No Labeling", with the difference that there will be a task in which the passively '
        'recorded sensors will take the name of the task during that specific task.'
    )
    
    info_text_partial_active_labelling = (
        'This mode is a combination of passive and active labeling, where sensors selected from the passive list will '
        'record without user interaction, and those selected from the active list will only be activated during the task '
        'of labeling.'
    )

    help_text_study_title = ('The study name')
    help_text_study_description = ('explanations of the study')
    help_text_study_isTest = ('If selected, the study is used foor testing purpose')
    help_text_study_duration = ('Number of days study is conducted')
    help_text_study_numberOfSubjects = ('Number of subjects required for whole study duration')
    help_text_study_passiveSensors = ('Sensors used in the study to record passively')
    help_text_study_activeSensors = ('Sensors used in the study to record actively')
    help_text_study_frequency = ('How many days before the question is repeated (0 ='
                                            'anytime, 1 = every day, etc.)')
    help_text_study_ema = ('Time in minutes when the answer to the question is reminded (480 = 8 hours = 08:00)')
    help_text_study_select_ema = ('Time in minutes when the answer to the question is reminded (480 = 8 hours = 08:00)')
    help_text_study_upload_ema_json = ('Time in minutes when the answer to the question is reminded (480 = 8 hours = 08:00)')
    help_text_study_upload_ema_images = ('Time in minutes when the answer to the question is reminded (480 = 8 hours = 08:00)')
    help_text_study_task_title = ('Time in minutes when the answer to the question is reminded (480 = 8 hours = 08:00)')
    help_text_study_task_description = ('Time in minutes when the answer to the question is reminded (480 = 8 hours = 08:00)')
    help_text_study_task_preparation = ('Time in minutes when the answer to the question is reminded (480 = 8 hours = 08:00)')
    help_text_study_task_duration = ('Time in minutes when the answer to the question is reminded (480 = 8 hours = 08:00)')

    
    help_text_survey_title = ('Name of the survey')
    help_text_survey_description = ('A short description of the survey (purpose, context)')
    help_text_survey_splitByCategory = ('If selected, questions are split into blocks')
    help_text_survey_scrolling = ('Select your choice of scrolling')
    help_text_survey_topN = ('Maximum number of questions to be answered in one session')
    help_text_survey_question_sortId = ('Question number for arranging the questions')
    help_text_survey_question_title = ('The question')
    help_text_survey_question_description = ('If necessary, explanations of the question')
    help_text_survey_question_type = ('Form of the expected answer (selection, time, text, number)')
    help_text_survey_question_category = ('Number for grouping questions into categories')
    help_text_survey_question_firstDayToAnswer = ('Day of the study on which the question is to be asked for the first time')
    help_text_survey_question_imageURL = ('Image source for the question, i.e. image1.png')
    help_text_survey_question_url = ('Link source for the question')
    help_text_survey_question_frequency = ('How many days before the question is repeated (0 ='
                                            'anytime, 1 = every day, etc.)')
    help_text_survey_question_clockTime = ('Time in minutes when the answer to the'
                                            'question is reminded (480 = 60*8 hours = 08:00)')
    help_text_survey_question_clockTime_start = ('Time when question becomes activated '
                                            '(the user also gets a push notification at that time).'
                                                 'Example entries: 480 for one '
                                                 'or 480, 700 for two time points (i.e. 480 = 60*8 hours = 08:00)')
    help_text_survey_question_clockTime_end = ('Time when question becomes deactivated '
                                               '(If multiple clocktime starts values are provided the number of clocktime end must match)')
    help_text_survey_category_activate_question = ('Enter List of questions to activate. '
                                                   'Example entries:1 or  2,3 ')
    help_text_survey_category_deactivate_question = ('Enter List of questions to deactivate. '
                                                    'Example entries:1 or 2,3 ')
    help_text_survey_category_activation_condition = ('Describe on what condition questions needs to be activated')
    help_text_survey_category_deactivation_condition = ('Describe on what condition questions needs to be deactivated')
    help_text_survey_question_deactivateOnAnswer = ('If a certain answer is given, the question is no longer asked')
    help_text_survey_question_deactivateOnDate = ('The question has an ‘expiration date’')
    help_text_survey_question_answerForm = ('Here you define options and placeholder texts based on the type')

    help_text_survey_category_title = ('The category name')
    help_text_survey_category_value = ('value in number which later used to assign to question')
    help_text_survey_category_didSubjectAsk = ('If selected, userId will be collected')
