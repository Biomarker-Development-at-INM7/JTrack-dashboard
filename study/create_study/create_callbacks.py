import base64
import json

from dash.exceptions import PreventUpdate
from exceptions.Exceptions import StudyAlreadyExistsException
from dash.dependencies import Output, Input, State
from study.Study import Study

from app import app


@app.callback([Output('create-study-output-state', 'children'),
               Output('create-study-name-input', 'value'),
               Output('create-study-duration-input', 'value'),
               Output('create-study-subject-number', 'value'),
               Output('create-study-description', 'value'),
               Output('create-study-sensors-list', 'value'),
               Output('frequency-list', 'value')],
              [Input('create-study-button', 'n_clicks')],
              [State('create-study-name-input', 'value'),
               State('create-study-duration-input', 'value'),
               State('create-study-subject-number', 'value'),
               State('create-study-description', 'value'),
               State('create-study-sensors-list', 'value'),
               State('frequency-list', 'value'),
               State('upload-ema-json', 'contents')])
def create_study_callback(n_clicks, study_name, study_duration, number_subjects, description, sensors, freq, ema_json):
    """
     Callback to create a new study on button click. Reacting if the create study button is clicked. Creates a new study
    if input field contains a valid input und the study does not exist yet.

    :param n_clicks: Click counter of create-study-button. Used to determine if button has ever been clicked. Given by
                Input('create-study-button', 'n_clicks')
    :param study_name: Name of the new study. Given by State('create-study-input', 'value')
    :param study_duration: Duration of study in days. Given by State('create-study-duration-input', 'value')
    :param number_subjects: Initial number of subjects enrolled. Subjects are stored with consecutive numbers in name. Given
                by State('create-study-subject-number', 'value')
    :param description: Study description
    :param sensors: List of selected sensors. Given by State('create-study-sensors-checklist', 'value')
    :param freq: Recording frequency
    :return: Output-state if creation was successful or if study already exists. Furthermore, clean input field of
                create-study-input and other fields. Input remains if creation is not successful.
                Returned by Output('create-study-output-state', 'children'), Output('create-study-input', 'value'),
                Output('create-study-duration-input', 'value'), Output('create-study-subject-number', 'value') and
                Output('create-study-sensors-checklist', 'value')
    """

    if n_clicks:
        content_type, content_string = ema_json.split(',')
        decoded = base64.b64decode(content_string)
        ema = json.loads(decoded)
        if not study_name or not study_duration or not sensors or not freq:
            error_output_state = ''
            if not study_name:
                error_output_state = 'Please enter a study name!'
            elif not study_duration:
                error_output_state = 'Please enter a study duration!'
            elif not sensors:
                error_output_state = 'Please select sensors!'
            elif not freq:
                error_output_state = 'Please enter a recording frequency!'
            return error_output_state, study_name, study_duration, number_subjects, description, sensors, freq

        else:
            sensors.append('ema')
            json_dict = {"name": study_name,
                         "duration": str(study_duration),
                         "number-of-subjects": str(number_subjects),
                         "description": description,
                         "sensor-list": sensors,
                         "enrolled-subjects": [],
                         "frequency": str(freq),
                         "survey": ema["survey"]}
            new_study = Study.from_json_dict(json_dict)
            try:
                new_study.create()
                return 'You created the study: ' + study_name, '', '', '', '', [], ''
            except StudyAlreadyExistsException:
                return study_name + ' already exists. Please chose another name!', '', study_duration, number_subjects, description, sensors, freq
    else:
        raise PreventUpdate