###########################################################################
####                models.py
####           Customised models
####           created by mnarava
####
####
###########################################################################
import uuid
from datetime import datetime,timezone, timedelta
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from jdash.apps import constants as constants


class Survey(models.Model): 
    """Class representing a Survey"""
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=1000) 
    topN = models.IntegerField(default = -1)
    splitbyCategory = models.BooleanField(default=False)
    scrolling = models.CharField(default='H',null=False,max_length=1,blank=False)
    owner = models.ForeignKey(User, on_delete=models.PROTECT,null=False, editable=False)
    createdDate = models.DateTimeField(default=datetime.now().astimezone())

    def __str__(self):
        return self.title or f"Survey #{self.pk}"
    
    
class Study(models.Model):
    """Class representing a Study"""
    is_test = models.BooleanField(default=False)
    title = models.CharField(max_length=500)   
    duration =  models.IntegerField(default=0)
    numberOfSubjects = models.IntegerField(default=0)
    description = models.TextField(max_length=1000,blank=True, null=True)
    enrolled_subjects = models.CharField(null=True,max_length=10000,blank=True)
    createdDate = models.DateTimeField(default=datetime.now().astimezone())
    owner = models.ForeignKey(User, on_delete=models.PROTECT, null=False, editable=False)

    passive_monitoring = models.BooleanField(default=False)
    frequency = models.IntegerField(default=50 , choices= constants.RECORDING_FREQUENCIES)
    sensor_list = models.CharField(max_length=150, default="",choices= constants.SENSORS_LIST)
    labeling = models.IntegerField(default=0,choices= constants.LABELLING)
    ecological_momentary_assessment = models.BooleanField(default=False)
    #check for how to store if ema is not choosen
    survey = models.OneToOneField(Survey,on_delete=models.PROTECT, blank=True, null=True)
    images = models.CharField(max_length=500,default="",blank=True )
    closed = models.BooleanField(default=False)
    def __str__(self):
        ret =  self.title 
        return ret
    
class Category(models.Model): 
    """Class representing a Category"""
    categoryTitle = models.CharField(max_length=55)
    categoryValue = models.IntegerField(default = 0)
    didSubjectAsk = models.BooleanField(default=False)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE,blank=True, null=True)

class Question(models.Model):
    """Class representing a Question"""
    sortId = models.IntegerField(default=1)
    title = models.TextField(max_length=10000)
    active = models.BooleanField(default=True)
    subText = models.TextField(max_length=1000,blank=True,null=True) 
    questionType = models.IntegerField( choices= constants.QUESTION_TYPES)
    category = models.IntegerField(default=1)
    imageURL = models.CharField(blank=True,max_length=100)
    url = models.CharField(blank=True,max_length=100)
    frequency = models.IntegerField(default=0)
    clockTime = models.IntegerField(default=0)
    clockTime_start = models.JSONField(default=list,blank=True, null=True)
    clockTime_end = models.JSONField(default=list,blank=True, null=True)
    clockTime_timezone = models.CharField(max_length=100, blank=True, null=True)
    nextDayToAnswer = models.IntegerField(default=0)
    deactivateOnAnswer = models.CharField(blank=True,max_length=5)
    deactivateOnDate = models.IntegerField(default=0)
    activate_question = models.JSONField(default=list,blank=True, null=True)
    deactivate_question = models.JSONField(default=list,blank=True, null=True)
    activation_condition = models.CharField(max_length=100,blank=True,null=True) 
    deactivation_condition = models.CharField(max_length=100,blank=True,null=True) 
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE,blank=True, null=True)

    def clean(self):
        """_summary_

        Raises:
            ValidationError: _description_
        """
        activate_question_list = self.activate_question
        deactivate_question_list = self.deactivate_question
        if not isinstance(activate_question_list, list):
            raise ValidationError({'activate_question': 'This field must be a list.'})
        
        if not isinstance(deactivate_question_list, list):
            raise ValidationError({'activate_question': 'This field must be a list.'})
        
        for item in activate_question_list:
            if not isinstance(item, (int)):
                raise ValidationError({'activate_question': 'All elements must be numbers (integers).'})
        
        # Check that every item in the list is a number (either integer or float)
        for item in deactivate_question_list:
            if not isinstance(item, (int)):
                raise ValidationError({'deactivate_question': 'All elements must be numbers (integers).'})
        if self.clockTime_start is not None and len(self.clockTime_start) > 1:
            if self.clockTime_end is not None:  
                if len(self.clockTime_start) != len(self.clockTime_end):
                    raise ValidationError("clockTime_start and clockTime_end must have the same number of elements.")
        super().clean()

class Answer(models.Model):
    """Class representing a Study"""
    answerSortId = models.IntegerField(default=1)
    text = models.TextField(max_length=10000,default="N")
    answerSubText = models.TextField(max_length=100,blank=True,null=False)
    value = models.FloatField(default=0.1)
    defaultValue = models.FloatField(default=0.1)
    stepSize = models.FloatField(default=0.1)
    minValue = models.FloatField(default=0.1)
    maxValue = models.FloatField(default=0.1)
    minText = models.CharField(max_length=100,blank=True)
    maxText = models.CharField(max_length=100,blank=True)
    question = models.OneToOneField(Question,on_delete=models.CASCADE,blank=False, null=False)



class Subject(models.Model):
    """Class representing a Subject"""
    appVersion_ema = models.TextField(max_length=10)
    applicationType = models.TextField(max_length=10)
    deviceBrand_ema = models.TextField(max_length=10)
    deviceModel_ema = models.TextField(max_length=10)
    osVersion_ema = models.TextField(max_length=10)
    deviceid_ema = models.TextField(max_length=500)
    status_ema = models.IntegerField(default=0)
    pushNotification_token_ema = models.TextField(max_length=1000)
    studyId = models.TextField(max_length=500)
    time_joined_ema = models.DateTimeField()
    time_left_ema = models.DateTimeField()
    username = models.TextField(max_length=100)
    study_duration = models.IntegerField(default=0)
    active_labeling = models.IntegerField(default=0)
    status = models.IntegerField(default=0)
    deviceBrand = models.TextField(max_length=10)
    deviceModel = models.TextField(max_length=10)
    osVersion = models.TextField(max_length=10)
    deviceid = models.TextField(max_length=500)
    pushNotification_token = models.TextField(max_length=1000)
    time_joined = models.DateTimeField()
    time_left = models.DateTimeField()
    timejoined_timezone = models.TextField(max_length=50)
    timeZoneOffSetMinutes = models.TextField(max_length=10)

# class Task(models.Model): 
#     """Class representing a Task"""
#     sortId = models.IntegerField(default=1)
#     task_title = models.CharField(max_length=100)
#     task_description = models.TextField(max_length=512)
#     task_preparation = models.IntegerField(default = 0)
#     task_duration = models.IntegerField(default = 0)
#     study = models.ForeignKey(Study, on_delete=models.PROTECT, blank=True, editable=False)


class FileDownloadToken(models.Model):
    """Class representing a FileDownloadToken"""
    code = models.CharField(max_length=6,default=000000)
    created_at = models.DateTimeField(default=datetime.now().astimezone())
    first_name = models.CharField(max_length=255,default="")
    email = models.EmailField(blank=True)
    file_name = models.CharField(max_length=1024)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    expiration_date = models.DateTimeField()
    status = models.CharField(max_length=20,default="")
    code_emailed = models.DateTimeField(default=datetime.now().astimezone())
    downloaded = models.DateTimeField(default=datetime.now().astimezone())
    link = models.CharField(max_length=10000,default="")

    def is_code_valid(self):
        """Check if the code is still valid (e.g., within 10 minutes of creation)."""
        return datetime.now().astimezone() - self.created_at <= timedelta(minutes=10)
    
    def is_token_valid(self):
        """Check if the token is still valid by comparing with the current time."""
        return datetime.now().astimezone() < self.token_expiration_date
class QualityControlTests(models.Model):
    """
    Generalized model to track test cases for study quality control.
    """

    testcase_id = models.CharField(
        max_length=20, unique=True, help_text="Unique identifier for the test case"
    )
    test_type = models.CharField(
        max_length=20,
        choices=constants.TEST_TYPE_CHOICES,
        help_text="Type of test case (e.g.,Notification, Sensor, EMA, Subject)",
    )
    description = models.TextField(help_text="Detailed description of the test case")
    steps = models.TextField(help_text="Expected outcome for this test case")
    expected_outcome = models.TextField(help_text="Expected outcome for this test case")
    tested_by_admin = models.BooleanField(default=False, help_text="Has the sensor data received?")
    tested_by_owner = models.BooleanField(default=False, help_text="Has the sensor data received ?")    
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp of creation")
    admin_updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp of last update")
    owner_updated_at = models.DateTimeField(auto_now=True, help_text="Timestamp of last update")
    admin_username = models.CharField(max_length=255)
    owner_username = models.CharField(max_length=255)
    study = models.ForeignKey(Study, on_delete=models.PROTECT, null=False, editable=False)

    def __str__(self):
        return f"TestCaseID: {self.testcase_id}"
