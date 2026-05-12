import logging , json
from jdash.forms import StudyDeviceSensorFormSet
from jdash.models import DeviceCatalog, StudyDeviceSensor
from jdash.utils.utils import question_db_list_serializer, normalize_question_refs
from jdash.config import constants as constants
from jdash.config.textmessages import TextMessages as textmessages
from django.utils.translation import gettext

logger = logging.getLogger("django")


def get_study_form_data(form,formset,request,study_device_formset, sensor_formsets):
    form_data = {}

    form_data['name'] = form.cleaned_data.get('study_label')
    form_data['description'] = form.cleaned_data.get('study_description')
    form_data['duration'] = form.cleaned_data.get('study_duration')
    form_data['number-of-subjects'] = form.cleaned_data.get('number_of_subjects') #need to remove later after mobile changes
    form_data['number_of_subjects'] = form.cleaned_data.get('number_of_subjects')
    form_data['ema_checkbox'] = form.cleaned_data.get('ema_checkbox')
    if form.cleaned_data.get('ema_checkbox'):
        if form.cleaned_data.get('survey') != '':
            form_data['survey'] = int(form.cleaned_data.get('survey'))
        if "json_file" in request.FILES and request.FILES["json_file"] :
            ema_json_file = request.FILES["json_file"].read()
            form_data['survey'] = json.loads(ema_json_file)
        if "images_zip_file" in request.FILES and request.FILES["images_zip_file"] :
            #handle_uploaded_file(request.FILES["images_zip_file"],form_data['name'])
            form_data['images']= True
        else:
            form_data['images']= False
    else:
        form_data['images']= False
    form_data['is_test'] = form.cleaned_data.get('is_test')
    #form_data['passive_checkbox'] = form.cleaned_data.get('passive_checkbox')
    form_data['frequency'] = form.cleaned_data.get('recording_freq')
    form_data['sensor_list_limited'] = form.cleaned_data.get('sensor_list_limited')
    form_data['sensor-list'] = form.cleaned_data.get('sensor_list') #need to remove later after mobile changes
    form_data['sensor_list'] = form.cleaned_data.get('sensor_list') 
    if formset.is_valid():
        form_data['task_list'] = [] 
        for taskform in formset:
            task = {}
            if (validate_empty(taskform.cleaned_data.get('task_name') )):
                task['task_name'] = taskform.cleaned_data.get('task_name')
                task['task_preparation'] = taskform.cleaned_data.get('task_preparation') if taskform.cleaned_data.get('task_preparation') != None else 0
                task['task_preparation_text'] = taskform.cleaned_data.get('task_preparation_text')
                task['task_duration'] = taskform.cleaned_data.get('task_duration')
                task['task_description'] = taskform.cleaned_data.get('task_description')
                form_data['task_list'].append(task)  
    else:
        form_data['task_list'] = [] 
    form_data[constants.field_name_labeling] = 0
    if len( form_data['task_list']) ==0 and len(form_data['sensor_list_limited'])  == 0: 
        form_data['active_labeling'] = 0
    
    if len( form_data['task_list']) > 0 and len(form_data['sensor_list_limited'])> 0 : 
        form_data['active_labeling'] = 1

    if len( form_data['sensor_list']) > 0 and len(form_data['task_list'])> 0 : 
        form_data['active_labeling'] = 2

    if len( form_data['sensor_list']) > 0 and len(form_data['sensor_list_limited'])> 0 : 
        form_data['active_labeling'] = 3


    form_data['wearables'] = get_study_device_config_json(study_device_formset, sensor_formsets)
    form_data["device_sensor_rows"] = get_study_device_config_rows_for_db(study_device_formset, sensor_formsets)  # ids for DB
    form_data['enrolled_subjects'] = []        
    form_data['enrolled-subjects'] = [] #need to remove later after mobile changes
    logger.info("form_data %s",form_data)
    return form_data

def get_study_device_config_rows_for_db(study_device_formset, sensor_formsets):
    """
    Returns a list of DB-ready rows (ids) from cleaned_data.
    Use this to create StudyDeviceSensor rows.
    """
    rows = []

    for i, dform in enumerate(study_device_formset.forms):
        if not dform.cleaned_data or dform.cleaned_data.get("DELETE"):
            continue

        device = dform.cleaned_data.get("device")
        if not device:
            continue

        sf = sensor_formsets[i]
        for sform in sf.forms:
            if not sform.cleaned_data or sform.cleaned_data.get("DELETE"):
                continue

            ds = sform.cleaned_data.get("device_sensor")  # DeviceSensor instance
            if not ds:
                continue

            # (optional) strict safety
            if ds.device_id != device.id:
                raise ValueError(
                    f"Device mismatch: selected device_id={device.id}, device_sensor.device_id={ds.device_id}"
                )

            # Resolution support is currently disabled in the study UI.
            # res = sform.cleaned_data.get("resolution")
            sr = sform.cleaned_data.get("sampling_rate")
            unit = sform.cleaned_data.get("unit")

            rows.append({
                "device_id": device.id,
                "device_sensor_id": ds.id,
                "sampling_rate_id": sr.id if sr else None,
                "unit_id": unit.id if unit else None,
            })

    return rows


def get_study_device_config_json(study_device_formset, sensor_formsets):
    
    """
    Returns JSON-serializable dict describing selected devices + sensors configuration.
    Assumes study_device_formset.is_valid() and all(sf.is_valid()) already called.
    """
    payload = {"devices": []}

    for i, dform in enumerate(study_device_formset.forms):
        if not dform.cleaned_data or dform.cleaned_data.get("DELETE"):
            continue

        device = dform.cleaned_data.get("device")
        if not device:
            continue

        dev_block = {
                "id": device.id,
                "sensorname": getattr(device, "name", None),
                "model": getattr(device, "model", None),            
                "sensors": [],
        }

        sf = sensor_formsets[i]

        for sform in sf.forms:
            if not sform.cleaned_data or sform.cleaned_data.get("DELETE"):
                continue

            ds = sform.cleaned_data.get("device_sensor")
            if not ds:
                continue

            # res = sform.cleaned_data.get("resolution")
            sr = sform.cleaned_data.get("sampling_rate")
            unit = sform.cleaned_data.get("unit")

            # Use override if present, otherwise fallback to mapping defaults
            # effective_resolution = (
            #     res.value if res else ds.default_resolution.value
            # )

            effective_sampling_rate = (
                sr.value if sr else ds.default_sampling_rate.value
            )

            effective_unit = (
                unit.value if unit else ds.default_unit.value
            )

            dev_block["sensors"].append({
                "wearable_sensor": ds.sensor.label,
                # "resolution": effective_resolution,
                "sampling_rate": effective_sampling_rate,
                "unit": effective_unit,
            })

        payload["devices"].append(dev_block)

    return payload["devices"]


def build_sensor_formsets(request_post_or_none, *, study, device_forms, prefix_base="sensors"):
    """
    Build one StudyDeviceSensorFormSet per device form index.
    - On GET: device id comes from dform.initial["device"]
    - On POST: device id comes from dform.cleaned_data["device"].
    """
    sensor_formsets = []

    for i, dform in enumerate(device_forms):
        sf_prefix = f"{prefix_base}-{i}"

        device_obj = None
        if request_post_or_none is None:
            device_id = (dform.initial or {}).get("device")
            if device_id:
                device_obj = DeviceCatalog.objects.filter(pk=device_id).first()
                qs = StudyDeviceSensor.objects.filter(
                    study=study,
                    device_sensor__device_id=device_id,
                )
            else:
                qs = StudyDeviceSensor.objects.none()
        else:
            if dform.cleaned_data and not dform.cleaned_data.get("DELETE"):
                device_obj = dform.cleaned_data.get("device")
            qs = StudyDeviceSensor.objects.filter(
                study=study,
                device_sensor__device=device_obj,
            ) if device_obj else StudyDeviceSensor.objects.none()

        sf = StudyDeviceSensorFormSet(
            request_post_or_none,
            prefix=sf_prefix,
            queryset=qs,
            device=device_obj,
        )
        sensor_formsets.append(sf)

    return sensor_formsets

def validate_empty(value):

    if (value != "" and value != None and value != "null"):
        return True
    return False

def get_survey_form_data(form):
    form_data = {}
    form_data["title"]= form.cleaned_data.get('title')
    form_data['description'] = form.cleaned_data.get('description')
    form_data['splitbyCategory'] = form.cleaned_data.get('splitbyCategory')
    form_data['scrolling'] = form.cleaned_data.get('scrolling')
    form_data["topN"]= -1

    logger.info("get_survey_form_data  cleaned date %s",form_data)
    return form_data


def get_question_form_data(form):
    form_data = {}
    form_data["title"]= form.cleaned_data.get('title')
    form_data["active"]= True
    form_data["sortId"]= form.cleaned_data.get('sortId')
    form_data['subText'] = form.cleaned_data.get('subText')
    form_data['frequency'] = form.cleaned_data.get('frequency')
    form_data['clockTime'] = form.cleaned_data.get('clockTime')
    form_data['clockTime_start'] = form.cleaned_data.get('clockTime_start')
    form_data['clockTime_end'] = form.cleaned_data.get('clockTime_end')
    form_data['activate_question'] = normalize_question_refs(form.cleaned_data.get('activate_question'))
    form_data['deactivate_question'] = normalize_question_refs(form.cleaned_data.get('deactivate_question'))
    form_data['activation_condition'] = form.cleaned_data.get('activation_condition') if form.cleaned_data.get('activation_condition') != None else ""
    form_data['deactivation_condition'] = form.cleaned_data.get('deactivation_condition') if form.cleaned_data.get('deactivation_condition') != None else ""
    form_data['nextDayToAnswer'] = form.cleaned_data.get('nextDayToAnswer') if form.cleaned_data.get('nextDayToAnswer') != None else 1
    form_data['category'] = form.cleaned_data.get('category')
    form_data['imageURL'] = form.cleaned_data.get('imageURL')
    form_data['url'] = form.cleaned_data.get('url')
    form_data['questionType'] = form.cleaned_data.get('questionType')
    form_data['deactivateOnAnswer'] = form.cleaned_data.get('deactivateOnAnswer')
    form_data['deactivateOnDate'] = form.cleaned_data.get('deactivateOnDate') if form.cleaned_data.get('deactivateOnDate') != None else 0
    form_data['clockTime_timezone'] = form.cleaned_data.get('clockTime_timezone') if form.cleaned_data.get('clockTime_timezone') != None else "Europe/Berlin"
    logger.info("get_question_form_data  cleaned date %s",form_data)
    return form_data


def get_answer_form_data(formset, question_type=None) -> dict:
    """
    Extracts and sanitizes answer data from a Django AnswerForm formset.

    Args:
        formset: Django formset containing AnswerForms.
        question_type (int, optional): Type of question (e.g., 1 or 2 for sortable answers).
            Determines if 'answerSortId' should be preserved.

    Returns:
        dict: A dictionary with key 'answers' containing a list of cleaned answer data.
    """
    data = {'answers': []}

    for index, answer in enumerate(formset.forms, start=1):
        if not answer.cleaned_data:
            continue  # Skip empty or invalid form entries

        cleaned = answer.cleaned_data
        logger.debug("Processing cleaned answer data: %s", cleaned)

        form_data = {
            "text": cleaned.get("text", ""),
            "answerSubText": cleaned.get("answerSubText", ""),
            "value": 0.1 if cleaned.get("value") is None else cleaned.get("value"),
            "defaultValue": 0.1 if cleaned.get("defaultValue") is None else cleaned.get("defaultValue"),
            "stepSize": 0.1 if cleaned.get("stepSize") is None else cleaned.get("stepSize"),
            "minValue": 0.1 if cleaned.get("minValue") is None else cleaned.get("minValue"),
            "maxValue": 0.1 if cleaned.get("maxValue") is None else cleaned.get("maxValue"),
            "minText": cleaned.get("minText", ""),
            "maxText": cleaned.get("maxText", "")
        }

        # Include sort ID only for sortable question types
        if question_type in [1, 2]:
            form_data["answerSortId"] = cleaned.get("answerSortId", index)

        data['answers'].append(form_data)

    return data

def get_blank_answer_object():
    answers = []
    answer = {}
    answer["answerSortId"] = 1
    answer["text"] = ""
    answer["answerSubText"] = "N"
    answer['value'] = 0.1
    answer['defaultValue'] = 0.1
    answer['stepSize'] = 0.1
    answer['minValue'] = 0.1
    answer['maxValue'] = 0.1
    answer['minText'] = ""
    answer['maxText'] = "" 
    answers.append(answer)
    return answers


def get_category_form_data(formset):
    form_data = {} 
    form_data['category_list'] = []
    for index, category_form in enumerate(formset, start=1):
        category = {}
        if (validate_empty(category_form.cleaned_data.get('categoryTitle') )):
            category['categoryTitle'] = category_form.cleaned_data.get('categoryTitle')
            category['categoryValue'] = index if category_form.cleaned_data.get('categoryValue') is None \
                                                else category_form.cleaned_data.get('categoryValue')
            #category['didSubjectAsk'] = category_form.cleaned_data.get('didSubjectAsk') 
            form_data['category_list'].append(category)  
    return form_data

def get_contactus_form_data(form):
    full_name = form.cleaned_data.get('fullname')
    email = form.cleaned_data.get('email')
    message = form.cleaned_data.get('message')

    return full_name,email,message

def get_notification_form_data(form):
    message_title = form.cleaned_data.get('message_title')
    message_text = form.cleaned_data.get('message_text')
    receivers = form.cleaned_data.get('receivers')

    return message_title,message_text,receivers


def get_info_texts():
    info_texts = {
        "ema": gettext(textmessages.info_text_ema),
        "passive_monitoring": gettext(textmessages.info_text_passive_monitoring),
        "no_labelling": gettext(textmessages.info_text_no_labelling),
        "active_labelling": gettext(textmessages.info_text_active_labelling),
        "manual_active_labelling": gettext(textmessages.info_text_manual_active_labelling),
        "partial_active_labelling": gettext(textmessages.info_text_partial_active_labelling)
    }

    return info_texts

 
def get_help_texts_for_survey_form():
    help_texts = {
        "title": gettext(textmessages.help_text_survey_title),
        "description": gettext(textmessages.help_text_survey_description),
        "splitbyCategory": gettext(textmessages.help_text_survey_splitByCategory),
        "scrolling": gettext(textmessages.help_text_survey_scrolling),
        "topN": gettext(textmessages.help_text_survey_topN),
    }

    return help_texts

def get_help_texts_for_question_form():
    help_texts = {
        "sortId": gettext(textmessages.help_text_survey_question_sortId),
        "title": gettext(textmessages.help_text_survey_question_title),
        "description": gettext(textmessages.help_text_survey_question_description),
        "category": gettext(textmessages.help_text_survey_question_category),
        "type": gettext(textmessages.help_text_survey_question_type),
        "firstDayToAnswer": gettext(textmessages.help_text_survey_question_firstDayToAnswer),
        "imageURL": gettext(textmessages.help_text_survey_question_imageURL),
        "url": gettext(textmessages.help_text_survey_question_url),
        "frequency": gettext(textmessages.help_text_survey_question_frequency),
        "clockTime": gettext(textmessages.help_text_survey_question_clockTime),
        "clockTime_start": gettext(textmessages.help_text_survey_question_clockTime_start),
        "clockTime_end": gettext(textmessages.help_text_survey_question_clockTime_end),
        "activate_question": gettext(textmessages.help_text_survey_category_activate_question),
        "deactivate_question": gettext(textmessages.help_text_survey_category_deactivate_question),
        "activation_condition": gettext(textmessages.help_text_survey_category_activation_condition),
        "deactivation_condition": gettext(textmessages.help_text_survey_category_deactivation_condition),
        "deactivateOnAnswer": gettext(textmessages.help_text_survey_question_deactivateOnAnswer),
        "deactivateOnDate": gettext(textmessages.help_text_survey_question_deactivateOnDate),
        "answerForm": gettext(textmessages.help_text_survey_question_answerForm),
    }

    return help_texts

def get_help_texts_for_category_form():
    help_texts = {
        "title": gettext(textmessages.help_text_survey_title),
        "value": gettext(textmessages.help_text_survey_description),
        "didSubjectAsk": gettext(textmessages.help_text_survey_splitByCategory)
    }

    return help_texts


def get_help_texts_for_study_form():
    help_texts = {
        "title": gettext(textmessages.help_text_survey_title),
        "description": gettext(textmessages.help_text_survey_description),
        "splitbyCategory": gettext(textmessages.help_text_survey_splitByCategory),
        "topN": gettext(textmessages.help_text_survey_topN),
    }

    return help_texts

def normalize_survey_data(json_meta):
    """
    Supports both formats:
    1. survey as dict:   {"survey": {"id": ..., "questions": [...]}}
    2. survey as string: {"survey": "{\"questions\": [...]}"}
    """
    survey = json_meta.get("survey")

    if isinstance(survey, dict):
        return survey

    if isinstance(survey, str):
        if not survey.strip():
            return {}

        try:
            parsed = json.loads(survey)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            logger.warning("Could not parse survey JSON string")

    return {}
