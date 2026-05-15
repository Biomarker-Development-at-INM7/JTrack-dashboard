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
from jdash.config import constants as constants
from django.utils import timezone as dj_timezone


    
class Survey(models.Model): 
    """Class representing a Survey"""
    title = models.CharField(max_length=100)
    description = models.TextField(max_length=1000) 
    topN = models.IntegerField(default = -1)
    splitbyCategory = models.BooleanField(default=False)
    scrolling = models.CharField(default='H',null=False,max_length=1,blank=False)
    owner = models.ForeignKey(User, default=1,on_delete=models.PROTECT,null=False, editable=False)
    createdDate = models.DateTimeField(default=dj_timezone.now)
    
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
    createdDate = models.DateTimeField(default=dj_timezone.now)
    owner = models.ForeignKey(User,default=1, on_delete=models.PROTECT, null=False, editable=False)

    passive_monitoring = models.BooleanField(default=False)
    frequency = models.IntegerField(default=50 , choices= constants.RECORDING_FREQUENCIES)
    sensor_list = models.JSONField( default=list,blank=True)
    sensor_list_limited = models.JSONField( default=list,blank=True)
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
    questionType = models.IntegerField(default= 0,choices= constants.QUESTION_TYPES)
    category = models.IntegerField(default=1)
    imageURL = models.CharField(blank=True,max_length=100)
    url = models.CharField(blank=True,max_length=100)
    frequency = models.IntegerField(default=0)
    clockTime = models.IntegerField(default=0)
    clockTime_start = models.JSONField(default=list,blank=True, null=True)
    clockTime_end = models.JSONField(default=list,blank=True, null=True)
    clockTime_timezone = models.CharField(max_length=100, blank=True, null=True)
    nextDayToAnswer = models.IntegerField(default=1)
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
        
        # Check that every item in the list is a number (only integers)
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
    question = models.ForeignKey(Question,on_delete=models.CASCADE,blank=False, null=False)



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
    deleted = models.BooleanField(default=False)


class DeviceCatalog(models.Model):
    """Class representing a Wearable Device Catalog"""
    name = models.CharField(max_length=255)  # e.g., "Garmin", "fitbit"
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    model = models.CharField(max_length=255, blank=True, null=True)
    device_type = models.CharField(max_length=50,
        choices=[
            ("watch", "Smartwatch"),
            ("band", "Fitness Band"),
            ("patch", "Wearable Patch"),
            ("ring", "Smart Ring"),
        ],
        blank=True
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name}    ({self.model})"

class SensorCatalog(models.Model):
    code = models.CharField(max_length=50)
    label = models.CharField(max_length=100)
    sensor_type = models.CharField(max_length=50,
        choices=[
            ("motion", "Motion"),
            ("physio", "Physiological"),
            ("location", "Location"),
            ("environmental", "Environmental"),
        ],
        blank=True
    )
    is_active = models.BooleanField(default=True)
    def __str__(self):
        return self.label


# # catalogs
# class ResolutionCatalog(models.Model):
#     value = models.CharField(max_length=100)
#     sensor = models.ForeignKey(SensorCatalog, default= 1,on_delete=models.PROTECT, related_name="sensor_resolutions")
#     class Meta:
#         constraints = [
#             models.UniqueConstraint(fields=["sensor", "value"], name="uniq_resolution_per_sensor")
#         ]
#     def __str__(self):
#         return self.value


class SamplingRateCatalog(models.Model):
    value = models.CharField(max_length=100)
    sensor = models.ForeignKey(SensorCatalog,default= 1, on_delete=models.PROTECT, related_name="sensor_sampling_rates")
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sensor", "value"], name="uniq_sampling_per_sensor")
        ]
    def __str__(self):
        return self.value


class UnitCatalog(models.Model):
    value = models.CharField(max_length=50)
    sensor = models.ForeignKey(SensorCatalog, default= 1, on_delete=models.PROTECT, related_name="sensor_units")
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["sensor", "value"], name="uniq_unit_per_sensor")
        ]
    def __str__(self):
        return self.value
         
class DeviceSensor(models.Model):
    device = models.ForeignKey(DeviceCatalog, on_delete=models.CASCADE, related_name="device_sensors")
    sensor = models.ForeignKey(SensorCatalog, on_delete=models.PROTECT, related_name="sensor_devices")

    #default_resolution = models.ForeignKey(ResolutionCatalog, on_delete=models.PROTECT )
    default_sampling_rate = models.ForeignKey(SamplingRateCatalog, on_delete=models.PROTECT)
    default_unit = models.ForeignKey(UnitCatalog, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["device", "sensor"], name="uniq_sensor_per_device")
        ]

    
    
    
    def __str__(self):
        return f"{self.device} - {self.sensor}"

    
class StudyDeviceSensor(models.Model):
    study = models.ForeignKey(Study, on_delete=models.PROTECT, related_name="study_device_sensors")
    device_sensor = models.ForeignKey(DeviceSensor, on_delete=models.PROTECT, related_name="study_configs")

    # optional overrides; if null => use defaults from device_sensor
    #resolution = models.ForeignKey(ResolutionCatalog, on_delete=models.PROTECT, null=True, blank=True)
    sampling_rate = models.ForeignKey(SamplingRateCatalog, on_delete=models.PROTECT, null=True, blank=True)
    unit = models.ForeignKey(UnitCatalog, on_delete=models.PROTECT, null=True, blank=True)

    is_enabled = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["study", "device_sensor"], name="uniq_device_sensor_per_study")
        ]

    
    
    
    
class Task(models.Model):
    """
    Model backing TaskForm (used as a formset in CreateStudyForm)
    Each Task is linked to a Study.
    """

    study = models.ForeignKey(
        Study,
        on_delete=models.PROTECT,
        related_name="tasks",
        editable=False
    )

    # task_name <-> task_name
    task_name = models.CharField(
        max_length=100,
        help_text="Name of the task."
    )

    # task_preparation <-> task_preparation (IntegerField, min=0 in form)
    task_preparation = models.IntegerField(
        default = 0,
        help_text="Preparation time for the task (e.g. minutes)."
    )

    # task_description <-> task_description
    task_preparation_text = models.TextField(
        blank=True,
        help_text="Optional description of the task."
    )

    # task_duration <-> task_duration (IntegerField, min=0 in form)
    task_duration = models.IntegerField(
        default = 0,
        help_text="Duration of the task (e.g. minutes)."
    )

    # task_description <-> task_description
    task_description = models.TextField(
        blank=True,
        help_text="Optional description of the task."
    )
    # sortId <-> sortId (PositiveIntegerField, min=1 in form)
    sortId = models.PositiveIntegerField(
        default=0,
        help_text="Order of the task within the study."
    )

    class Meta:
        ordering = ["sortId", "id"]

    def save(self, *args, **kwargs):
        if self._state.adding and not self.sortId:
            max_sort_id = (
                Task.objects
                .filter(study=self.study)
                .aggregate(max_sort_id=models.Max("sortId"))
                .get("max_sort_id")
                or 0
            )
            self.sortId = max_sort_id + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.study.title} - {self.task_name}"
    

class FileDownloadToken(models.Model):
    """Class representing a FileDownloadToken"""
    code = models.CharField(max_length=6,default=000000)
    created_at = models.DateTimeField(default=dj_timezone.now)
    first_name = models.CharField(max_length=255,default="")
    email = models.EmailField(blank=True)
    file_name = models.CharField(max_length=1024)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    expiration_date = models.DateTimeField()
    status = models.CharField(max_length=20,default="")
    code_emailed = models.DateTimeField(default=dj_timezone.now)
    downloaded = models.DateTimeField(default=dj_timezone.now)
    link = models.CharField(max_length=10000,default="")

    def is_code_valid(self):
        """Check if the code is still valid (e.g., within 10 minutes of creation)."""
        return dj_timezone.now - self.created_at <= timedelta(minutes=10)
    
    def is_token_valid(self):
        """Check if the token is still valid by comparing with the current time."""
        return dj_timezone.now() < self.expiration_date
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

class QualityControlComment(models.Model):
    """Comment history entries for a quality-control test case."""

    test_case = models.ForeignKey(
        "jdash.QualityControlTests",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    text = models.TextField()
    username = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    display_timestamp = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"QCComment({self.test_case_id}, {self.username})"
