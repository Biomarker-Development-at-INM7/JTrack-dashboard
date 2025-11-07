from django import template
from django.contrib.auth.models import Group
from jdash.classes.subject import Subject
from jdash.apps import constants as constants
register = template.Library()

@register.filter(name='get_n_batches')  
def get_n_batches(value, arg):
    return value[arg+ " n_batches"]

@register.filter(name='get_last_time_received')  
def get_last_time_received(value, arg):
    return value[arg+ " last_time_received"] 

@register.filter(name='get_activity_status_tag') 
def get_activity_status_tag(value,studyobj):
    subject_instance = Subject(value)
    activity_status_code = Subject.get_activity_status_code(subject_instance,studyobj)
    if activity_status_code == 0:
        return '<span class="text-danger" data-toggle="tooltip" data-placement="top" title="'+constants.no_data+'"  >'+value["subject_name"]+'</span>'
    elif activity_status_code == 1:
        return '<span class="text-primary" data-toggle="tooltip" data-placement="top" title="'+constants.left_early+'" >'+value["subject_name"]+'</span>'
    elif activity_status_code == 2:
        return '<span class="text-warning" data-toggle="tooltip" data-placement="top" title="'+constants.duration_reached_left+'" >'+value["subject_name"]+'</span>'
    elif activity_status_code == 3:
        return '<span class="text-success" data-toggle="tooltip" data-placement="top" title="'+constants.duration_reached+'" >'+value["subject_name"]+'</span>'
    elif activity_status_code == 4:
        return '<span class="text-info" data-toggle="tooltip" data-placement="top" title="'+constants.multiple_qr+'" >'+value["subject_name"]+'</span>'

@register.filter(name='get_status_tag') 
def get_status_tag(value):
    if value == 0:
        return '<strong><span class="text-warning" data-toggle="tooltip" data-placement="top" title="Everything is fine" >Instudy</span></strong>'
    elif value == 1:
        return '<strong><span class="text-primary" data-toggle="tooltip" data-placement="top" title="Subject left study with this QR Code" >Left study</span></strong>'
    elif value == 2:
        return '<strong><span class="text-success" data-toggle="tooltip" data-placement="top" title="Subject reached study duration and left automatically"  >Completed</span></strong>'
    elif value == 3:
        return '<strong><span class="text-danger" data-toggle="tooltip" data-placement="top" title="Subject removed by dashboard" >Removed</span></strong>'

@register.filter(name='get_sensor_tag') 
def get_sensor_tag(value,studyobj):
    returnString = ""
    btn_class= "btn-danger"
    subject_instance = Subject(value,None)
    sesnor_dict =  subject_instance.get_sensor_activity_code(value,studyobj)
    if sesnor_dict != "":
        for k,v in sesnor_dict.items():
            if v["status_code"] == 1:
                btn_class = "btn-primary"
            elif v["status_code"] == 2:
                btn_class = "btn-warning"
            elif v["status_code"] == 3:
                btn_class = "btn-success"
            

            returnString = returnString + '<button style= " margin-left:2px" class="btn '+btn_class+' " data-toggle="tooltip" data-placement="top" title="'+v["status_desc"]+'" >'+v["sensor_code"]+'</button>'
    return returnString

@register.filter(name="get_sensor_codes")
def get_sensor_codes(sensor_list,current_sensor_list):
    bufferStr = ""
    if isinstance(sensor_list, str):
        res = [sensor_list]
        sensor_list = res
    for sensor in  sensor_list:
        temp = constants.sensor_list[sensor] 
        if sensor in current_sensor_list:
            bufferStr = bufferStr  + '<button style= " margin-left:2px" class="btn btn-light today-sensor" data-toggle="tooltip" data-placement="top" title="'+sensor+'" >'+temp+'</button>'
        else:
            bufferStr = bufferStr  + '<button style= " margin-left:2px" class="btn btn-light" data-toggle="tooltip" data-placement="top" title="'+sensor+'" >'+temp+'</button>'
    return bufferStr  



@register.filter(name="get_size")
def get_size(obj):
    return len(obj)

@register.filter(name="get_text")
def get_text(obj):
    choicesStr = ""
    
    for answer in obj:
        choicesStr = choicesStr + answer["text"] + ";"

    return choicesStr


@register.filter(name="get_item")
def get_item(lst, index):
    try:
        return lst[index]["db_id"]
    except (IndexError, TypeError):
        return None

@register.filter(name="get_subText")
def get_subText(obj):
    for answer in obj:
        if "subText" in answer:
            return answer["subText"]

@register.filter(name="get_id")
def get_id(obj):
    idStr = ""
    for answer in obj:
        if "db_id" in answer:
            idStr = idStr + str(answer["db_id"]) + ";"
    return idStr

@register.filter(name="get_sortId")
def get_sortId(obj):
    for answer in obj:
        if "id" in answer:
            return answer["id"]

@register.filter(name="get_value")
def get_value(obj):
    for answer in obj:
        return answer["value"]

@register.filter(name="get_defaultValue")
def get_defaultValue(obj):
    for answer in obj:
        return answer["defaultValue"]
    
@register.filter(name="get_stepSize")
def get_stepSize(obj):
    for answer in obj:
        return answer["stepSize"]

@register.filter(name="get_minVal")
def get_minVal(obj):
    for answer in obj:
        if "minVal" in answer:
            return answer["minVal"]
        else:
            return answer["minValue"]

@register.filter(name="get_maxVal")
def get_maxVal(obj):
    for answer in obj:
        
        if "maxVal" in answer:
            return answer["maxVal"]
        else :      
            return answer["maxValue"]

@register.filter(name="get_minText")
def get_minText(obj):
    for answer in obj:
        return answer["minText"]
    
@register.filter(name="get_maxText")
def get_maxText(obj):
    for answer in obj:
        return answer["maxText"]
    


@register.filter(name="get_question_category")
def get_question_category(value):
    if value == 0:
        return 'Instruction for questions'
    elif value == 1:
        return 'Single Choice'
    elif value == 2:
        return 'Multiple Choice'
    elif value == 4:
        return 'Free Text'
    elif value == 5:
        return 'Free Number'
    elif value == 3:
        return 'Sliding'
    elif value == 6:
        return 'Time'
    elif value == 7:
        return 'Date'
    elif value == 8:
        return 'Time and Date'
    elif value == 9:
        return 'Duration'

@register.filter(name='has_group')
def has_group(user, group_name):
    group = Group.objects.get(name=group_name)
    return True if group in user.groups.all() else False

