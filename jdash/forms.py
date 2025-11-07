from django import forms
from django.utils.safestring import mark_safe
from django.forms import formset_factory
from django.core.validators import RegexValidator
from django.forms import widgets
from django.forms.widgets import Widget
from jdash.models import Answer, Question, Study, Survey, Category
from jdash.apps import constants as constants


TITLE_REGEX = RegexValidator(r'^[a-zA-Z0-9_]*$','Only alphanumeric characters are allowed in study label.')

class TaskForm(forms.Form):
    """Class representing a TaskForm"""
    task_name = forms.CharField(widget=forms.TextInput(  
        attrs={
            'class': 'form-control'
        }
    ), label = False,
    required=False)
    task_preparation = forms.IntegerField(widget=forms.NumberInput(  
        attrs={
      
            'class': 'form-control'
        }
    ), min_value= 0 ,label = False,
    required=False)
    task_duration = forms.IntegerField(widget=forms.NumberInput(  
        attrs={
      
            'class': 'form-control'
        }
    ), min_value= 0 ,label = False,
    required=False)

    task_description = forms.CharField(widget=forms.Textarea(  
        attrs={
            'rows' : 2,
            'class': 'form-control'
        }
    ), label = False,
    required=False)

    def __init__(self, *args, **kwargs):
        #self.extra = kwargs.pop('extra', self.extra)
        super(TaskForm, self).__init__(*args, **kwargs)
        

class CreateStudyForm(forms.Form):
    """Class representing a CreateStudyForm"""
    study_label = forms.CharField(widget=forms.TextInput(  
        attrs={
            'class': 'form-control'
        }
    ), label = False,validators=[TITLE_REGEX])
    
    study_duration = forms.IntegerField(widget=forms.NumberInput(  
        attrs={
            'class': 'form-control'
        }
    ), min_value= 0 ,label = False)
    number_of_subjects = forms.IntegerField(widget=forms.NumberInput(  
        attrs={
            'class': 'form-control'
        }
    ), min_value= 0 ,label = False)
    study_description = forms.CharField(widget=forms.Textarea(  
        attrs={
            'rows' : 4,
            'class': 'form-control'
        }
    ), label = False)
    is_test = forms.BooleanField(widget=forms.CheckboxInput(
        attrs={
            'class': 'form-check-input ',
            'id' : "test_study"
        }
    ),required=False)
    ema_checkbox = forms.BooleanField(widget=forms.CheckboxInput(
         attrs={
            'class': 'form-check-input position-static',
            'onclick' : "show('ecological_momentary_form', this)",
            'placeholder': 'Ecological momentary assessment',
            'id' : "ecological_form_checkbox"
        }
    ),required=False)

    survey = forms.ChoiceField(choices=(),widget=forms.Select(
        attrs={
            'class' : 'form-control' 
        }


    ), required=False)

    json_file = forms.FileField(widget= forms.FileInput(
        attrs={
            'name' : "json_file",
            'class' : "file-input",
             'type' : "file"
        }
    )
    ,required=False)

    images_zip_file = forms.FileField(widget= forms.FileInput(
        attrs={
            'name' : "images_zip_file",
            'class' : "file-input",
            'type' : "file"
        }
    )
    ,required=False)

    passive_checkbox = forms.BooleanField(widget=forms.CheckboxInput(
         attrs={
            'class': 'form-check-input',
            'onclick' : "show('passive_monitoring_form', this)",
            'id' : "passive_form_checkbox"
        }
    ),required=False,label=True)

    recording_freq = forms.IntegerField(label=True,widget=forms.Select(
        attrs={
            'class' : 'form-control' 

        },
        choices=constants.RECORDING_FREQUENCIES
    ), required=False)

    sensor_list = forms.MultipleChoiceField(choices=constants.SENSORS_LIST,widget=forms.SelectMultiple(
        attrs={
            'class' : 'form-control',
            'style': 'height: 200px;' 
        }
    
        
    ), required=False)


    active_labeling= forms.IntegerField(label='Labeling option', widget=forms.RadioSelect(
        attrs={
            'class' : 'form-check-inline ' ,
            'id' : "labelling",
            'data-toggle': 'tooltip',
            'title' : "tooltip on radio!",
            'onChange':"show_task_form()"
        },
        choices=constants.LABELLING
        ),required=False)

    sensor_list_limited = forms.MultipleChoiceField(choices=constants.SENSORS_LIST,widget=forms.SelectMultiple(
        attrs={
            'class' : 'form-control' ,
           'id' : "sensor_list_limited",
            'style': 'height: 200px;' ,
        }
    ), required=False)

    taskformset = formset_factory(TaskForm)
    
    
    def __init__(self, *args, **kwargs):
        survey = kwargs.pop('survey', [])
        initial_survey_id = kwargs.pop('initial_survey_id', None)
        json_data = kwargs.pop('data', None)
        super(CreateStudyForm, self).__init__(*args, **kwargs)

        self.fields['survey'].choices = [('', 'Select survey')] + [(data['id'], data['title']) for data in survey]

        if json_data != None:
            
            self.fields['study_label'].initial = json_data["name"]
            self.fields['study_duration'].initial = json_data["duration"]
            self.fields['number_of_subjects'].initial = json_data["number_of_subjects"]
            self.fields['study_description'].initial = json_data["description"]


            if "survey" in json_data:
                self.fields['ema_checkbox'].initial = True
                if "id" in json_data["survey"]:
                    self.fields['survey'].initial = initial_survey_id
                else:
                    self.fields['survey'].choices = [('', 'Select survey')] + [(data['id'], data['title']) for data in survey]
            else:
                self.fields['survey'].choices = [('', 'Select survey')] + [(data['id'], data['title']) for data in survey]

            if "is_test" in json_data:   
                self.fields['is_test'].initial = json_data["is_test"]
            if 'sensor_size' in json_data and json_data['sensor_size'] > 0:
                self.fields['passive_checkbox'].initial = True
                self.fields['recording_freq'].initial = json_data["frequency"]
                self.fields['sensor_list'].initial = json_data["sensor_list"] 
            if 'active_labeling' in json_data:
                self.fields['active_labeling'].initial = json_data['active_labeling']
                if json_data['active_labeling'] == 3 and 'sensor_list_limited' in json_data:
                    self.fields['sensor_list_limited'].initial = json_data['sensor_list_limited']
            
                                

    class Meta:
        model = Study
        fields = '__all__'
        

RECEIVER_ID_LIST = []
class SendNotificationForm(forms.Form):
    """Class representing a SendNotificationForm"""
    message_title =  forms.CharField(widget=forms.TextInput(
        attrs={
            'class' : 'form-control',
            'placeholder': 'Message title'
        }
    ), label = False)
    message_text = forms.CharField(widget=forms.Textarea(
        attrs={
            'rows' : 4,
            'class' : 'form-control' ,
            'placeholder': 'Message text'
        }
    ), label = False)
    receivers = forms.MultipleChoiceField(choices = (),widget=forms.SelectMultiple(
        attrs={
            'class' : 'form-control' ,
           'placeholder': 'Receivers',
           'id' :"id-choices" 
        }
    ), label = False )

    def __init__(self, *args, **kwargs):
        receivers = kwargs.pop('receivers', None)
        super(SendNotificationForm, self).__init__(*args, **kwargs)
        self.fields['receivers'].choices = [ (v, v.split(";")[0]) for k, v in enumerate(receivers)  ]

    class Meta:
        fields = '__all__'
    


class RemoveSubjectsForm(forms.Form):  
    """Class representing a RemoveSubjectsForm""" 
    subject_to_remove = forms.ChoiceField(choices=(),widget=forms.Select(
        attrs={
            'class' : 'form-control' 
        }
    ), label = False)
    
    def __init__(self, *args, **kwargs):
        receivers = kwargs.pop('receivers', None)
        super(RemoveSubjectsForm, self).__init__(*args, **kwargs)
        self.fields['subject_to_remove'].choices = [ (v, v.split(";")[0]) for k, v in enumerate(receivers)  ]
    class Meta:
        fields = '__all__'


class CreateSubjectForm(forms.Form):
    """Class representing a CreateSubjectForm""" 
    number_of_subjects = forms.IntegerField(widget=forms.NumberInput(
        attrs={
            'class' : 'form-control',
            'placeholder': 'Number of Subjects'
        }
    ),label = False, min_value=0)
    class Meta:
        fields = '__all__'


class JSONUploadForm(forms.Form):
    """Form representing a create survey from json upload""" 
    json_file = forms.FileField(widget= forms.FileInput(
        attrs={
            'name' : "json_file",
            'class' : "form-control",
             'type' : "file"
        }
    ))

class SurveyForm(forms.ModelForm):
    """Class representing a SurveyForm"""

    def __init__(self, *args, **kwargs):

        json_data = kwargs.pop('data', None)
        super(SurveyForm, self).__init__(*args, **kwargs)
    
        if json_data is not None:
            self.fields['title'].initial = json_data["title"]
            self.fields['description'].initial = json_data["description"]
            self.fields['splitbyCategory'].initial = json_data["splitbyCategory"]
            self.fields['scrolling'].initial = json_data["scrolling"]
            self.fields['topN'].initial = json_data["topN"]

    class Meta:
        model = Survey
        fields = ['title', 'description', 'splitbyCategory','scrolling' ,'topN']
        exclude = ['id','study']
        widgets = {
            'title' : forms.TextInput(attrs={
                'id' : 'surveyTitle'
                }),
            'description': forms.Textarea(attrs={'rows' : 4}),
            'splitbyCategory' : forms.CheckboxInput(
                attrs={
                'class' : 'form-check-input',
                'placeholder' : 'Use default values for below form'  ,
                'id' : 'splitCheck',

                }
            ),
            'scrolling' : forms.RadioSelect(
                choices= constants.SCROLLING_CHOICES
            ),
            'topN' : forms.NumberInput(attrs={
                'placeholder': 'TopN'})  
        }
        
    
class CategoryForm(forms.ModelForm):
    """Class representing a ModelForm"""

    def __init__(self, *args, **kwargs):
        super(CategoryForm, self).__init__(*args, **kwargs)
        self.fields['categoryTitle'].required = False
        #self.fields['didSubjectAsk'].required = False
        #self.fields['categoryValue'].required = False
        
    class Meta:
        model = Category
        fields = ['categoryTitle']
        exclude = ['id','survey']
        widgets = {
            'categoryTitle' : forms.TextInput(attrs={
                 'class': 'form-control'}),
            'categoryValue' : forms.NumberInput(attrs={
                 'class': 'form-control'})
            # 'didSubjectAsk' : forms.CheckboxInput(
            #     attrs={
            #     'class' : 'form-check-input'

            #     }
            # ),
        }

class AnswerForm(forms.ModelForm):
    """Class representing a AnswerForm"""
    
    def __init__(self, *args, **kwargs):
        super(AnswerForm, self).__init__(*args, **kwargs)
        self.fields['text'].required = False
        self.fields['answerSubText'].required = False
        self.fields['answerSortId'].required = False
        self.fields['value'].required = False
        self.fields['defaultValue'].required = False
        self.fields['stepSize'].required = False
        self.fields['minValue'].required = False
        self.fields['maxValue'].required = False
        self.fields['maxText'].required = False
        self.fields['minText'].required = False

            
    class Meta:
        model = Answer
        exclude = ['question']
        fields = '__all__'
        widgets = {
            'text': forms.TextInput( ),
            'answerSubText': forms.TextInput( 
            ),
            'answerSortId' : forms.NumberInput(
                ),
            'value' : forms.NumberInput(  
                    attrs={
                        'step': "0.1"
                        
                    }
                ),
            'defaultValue' : forms.NumberInput(  
                    attrs={
                        'step': "0.1"
                    }
                ),
            'stepSize' :forms.NumberInput(  
                    attrs={
                        'step': "0.1"
                    } 
                ),
            
            'minValue' : forms.NumberInput(  
                    attrs={
                        'step': "0.1"
                    }
                ),
            'maxValue' : forms.NumberInput(  
                attrs={
                    'step': "0.1"
                }
            ),
            'minText': forms.TextInput(  
                attrs={
                }
            ),
            'maxText': forms.TextInput(  
                attrs={
                }
            )

        }



class BlankIfEmptyJSONField(forms.JSONField):
    def prepare_value(self, value):
        # whenever the value is “nothing” (None, empty list, empty dict),
        # return the empty string so the widget renders blank
        if value in (None, [], {},""):
            return ''

        if isinstance(value, str):
            s = value.strip()

            # If it’s surrounded by quotes, remove them:
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                s = s[1:-1].strip()

            # If it’s JSON‐bracketed, e.g. "[480,560,800]", drop the brackets:
            if s.startswith("[") and s.endswith("]"):
                inner = s[1:-1].strip()
                # Now `inner` might be "480,560,800" or "480", "560", "800" etc.
                # Since JSONField’s normal parsing would accept [1,2,3], but we want the bare CSV,
                # returning `inner` is fine (no quotes).
                return inner

            # Otherwise, just return the string as‐is (e.g. "480,560,800" no extra quotes).
            return s

        return super().prepare_value(value)
        
    def to_python(self, value):
        # When the form posts back an empty string, convert to []
        if value in ('', None):
            return []

        if not isinstance(value, str):
            return super().to_python(value)

        # 3) It’s a string. If it doesn’t look like JSON (no leading “[” or “{”), treat it as CSV:
        s = value.strip()
        if not (s.startswith("[") or s.startswith("{")):
            # Split on commas, strip whitespace, and return a list of strings (or ints):
            parts = [chunk.strip() for chunk in s.split(",") if chunk.strip()]
            # If you want numbers instead of strings, map int():
            try:
                return [int(p) for p in parts]
            except ValueError:
                return parts

        return super().to_python(s)


class QuestionForm(forms.ModelForm):
    """
    A ModelForm class for creating and updating 
    question forms with optional default settings.
    """
    
    default_value = forms.BooleanField(widget=forms.CheckboxInput(
        attrs={
           'class' : 'form-check-input',
           'placeholder' : 'Use default values for below form'  ,
           'id' : 'flexSwitchCheckDefault',
           'onclick' : 'set_default_values(this)'

        }
    ),label = True,required=False)
    title = forms.CharField(widget=forms.Textarea(
                attrs={
                    'id' :"questionTitle",
                    'rows' : 2
                    } )
                , required=True,label = False)
    subText = forms.CharField(widget=forms.TextInput(
        attrs={
            'id' :"subText"
        }
    ), label = False)
    questionType = forms.ChoiceField(choices=constants.QUESTION_TYPES,widget=forms.Select(
        attrs={
             'id' :"questionType",
            'onChange':"show_answer_form()"
        }),
        label = False)
    imageURL = forms.CharField(widget=forms.TextInput(
        attrs={
            'id' :"imageURL"
        }
    ), label = False)
    url = forms.CharField(widget=forms.TextInput(
        attrs={
            'id' :"url"
        }
    ), label = False)
    frequency = forms.IntegerField(widget=forms.NumberInput(
        attrs={
            'id' : 'frequency'
        }
    ), label = False)
    category = forms.ChoiceField(choices=(),widget=forms.Select(
        attrs={
            'id' : 'category'
        }
    ), label = False)
    nextDayToAnswer = forms.IntegerField(widget=forms.NumberInput(
        attrs={
            'id' : 'nextDayToAnswer'
        }
    ), label = False)
    deactivateOnDate = forms.IntegerField(widget=forms.NumberInput(
        attrs={
            'id' : 'deactivateOnDate'
        }
    ), label = False)
    deactivateOnAnswer = forms.CharField(widget=forms.TextInput(
        attrs={
            'id' :"deactivateOnAnswer"
        }
    ), label = False)
    sortId = forms.IntegerField(widget=forms.NumberInput(
        attrs={
            'id' : 'sortId'
        }
    ), label = False)
    clockTime = forms.IntegerField(widget=forms.NumberInput(    
        attrs={
            'id' : 'clockTime'
        }
    ), label = False)
    active = forms.BooleanField(widget=forms.CheckboxInput(
        attrs={
             'id' :"active"
        }
    ), label = False)
    category = forms.IntegerField(widget=forms.NumberInput(
        attrs={
            'id' : 'category'
        }
    ), label = False)
    activation_condition = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'id' :"activation_condition"
            }
        ),
        help_text="List of conditions (leave blank if none)"
    )
    deactivation_condition = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'id' :"deactivation_condition"
            }
        ),
        help_text="List of conditions (leave blank if none)"
    )    
    activate_question = BlankIfEmptyJSONField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows' : 1,
                'id' :"activate_question",
                'oninput' : "toggleActivateConditionsField()"
            }
        ),
        help_text="List of question (leave blank if none)"
    )
    deactivate_question = BlankIfEmptyJSONField(
        required=False,
        widget=forms.Textarea(
            attrs={
                 'rows' : 1,
                    'id' :"deactivate_question",
                    'oninput' : "toggleDeactivateConditionsField()"
            }
        ),
        help_text="List ofquestion (leave blank if none)"
    )
    
    clockTime_start = BlankIfEmptyJSONField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': 1,
                'id' :"clockTime_start"
            }
        ),
        help_text="List of start times (leave blank if none)"
    )
    clockTime_end = BlankIfEmptyJSONField(
        required=False,
        widget=forms.Textarea(
            attrs={
                'rows': 1,
                'id' :"clockTime_end"
            }
        ),
        help_text="List of start times (leave blank if none)"
    )
    
    answer_formset = formset_factory(AnswerForm)
    def __init__(self, *args, categories=None, **kwargs):
        json_data = kwargs.pop('data', None)
        super(QuestionForm, self).__init__(*args, **kwargs)
        
            
        if json_data is not None:
            self.fields['title'].initial = json_data["title"]
            self.fields['active'].initial = json_data["active"] 
            self.fields['subText'].initial = json_data["subText"]
            self.fields['questionType'].initial = json_data["questionType"]
            self.fields['category'].initial = json_data["category"]
            self.fields['imageURL'].initial = json_data["imageURL"]
            self.fields['url'].initial = json_data["url"]
            self.fields['nextDayToAnswer'].initial = json_data["nextDayToAnswer"]
            self.fields['deactivateOnDate'].initial = json_data["deactivateOnDate"]
            self.fields['deactivateOnAnswer'].initial = json_data["deactivateOnAnswer"]
            self.fields['sortId'].initial = json_data["sortId"]
            self.fields['frequency'].initial = json_data["frequency"]
            self.fields['clockTime'].initial = json_data["clockTime"]
            self.fields['clockTime_start'].initial = json_data["clockTime_start"]
            self.fields['clockTime_end'].initial = json_data["clockTime_end"]
            self.fields['activate_question'].initial = json_data["activate_question"]
            self.fields['deactivate_question'].initial = json_data["deactivate_question"]
            self.fields['activation_condition'].initial = json_data["activation_condition"]
            self.fields['deactivation_condition'].initial = json_data["deactivation_condition"]
            
        self.fields['title'].required = False
        self.fields['active'].required = False
        self.fields['subText'].required = False
        self.fields['questionType'].required = False
        self.fields['category'].required = False
        self.fields['imageURL'].required = False
        self.fields['url'].required = False
        self.fields['nextDayToAnswer'].required = False
        self.fields['deactivateOnDate'].required = False
        self.fields['deactivateOnAnswer'].required = False
        self.fields['clockTime'].required = False
        self.fields['sortId'].required = True
        self.fields['clockTime_start'].required = False
        self.fields['clockTime_end'].required = False
        self.fields['activate_question'].required = False
        self.fields['deactivate_question'].required = False
        self.fields['activation_condition'].required = False
        self.fields['deactivation_condition'].required = False

        # Conditionally set category field widget
        if categories is not None and len(categories) > 0:
            # If categories exist, show dropdown (Select)
            self.fields['category'].widget = forms.Select(
                choices=[(category['categoryValue'], category['categoryTitle']) for category in categories],
                attrs={
                    'id': 'category',
                    'class': 'form-control'
                }
            )

        
            
    class Meta:
        model = Question
        exclude = ['survey']
        fields = '__all__'



class DeleteSubjectForm(forms.Form):
    """Class representing a DeleteSubjectForm"""
    subjectId = forms.CharField(widget=forms.TextInput(  
        attrs={
            'class': 'form-control',
            'placeholder': 'Subject ID'
        }
    ), label = False)

    email = forms.EmailField(widget=forms.EmailInput(
        attrs = {
            'class': 'form-control',
            'placeholder': 'Email'
        }
    ))
    reason = forms.CharField(widget=forms.Textarea(
        attrs={
            'rows' : 5,
            'class': 'form-control',
            'placeholder': 'Reason'
        }
    ), label = False)


    class Meta:
        fields = '__all__'

class ContactUsForm(forms.Form):
    """Class representing a ContactUsForm"""
    fullname = forms.CharField(widget=forms.TextInput(  
        attrs={
            'class': 'form-control',
            'placeholder': 'Full Name'
        }
    ), label = False)
    email = forms.EmailField(widget=forms.EmailInput(
        attrs = {
            'class': 'form-control',
            'placeholder': 'Email'
        }
    ))
    message = forms.CharField(widget=forms.Textarea(  
        attrs={
            'rows' : 10,
            'class': 'form-control',
            'placeholder': 'Message'
        }
    ), label = False)

    class Meta:
        fields = '__all__'


class DateForm(forms.Form):
    """Class representing a DateForm"""
    start = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        fields = '__all__'
