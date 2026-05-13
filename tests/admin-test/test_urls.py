from django.test import SimpleTestCase
from django.urls import reverse, resolve
from jdash import views
from jdash.apps import constants

class URLResolutionTests(SimpleTestCase):
    def test_home_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_home)).func, views.index)

    def test_login_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_login)).func, views.login_request)

    def test_logout_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_logout)).func, views.logout_request)

    def test_contact_email_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_contact_email)).func, views.contact_email)

    def test_add_study_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_add_study)).func, views.add_study)

    def test_edit_study_url(self):
        url = reverse(constants.url_name_for_edit_study, args=["teststudy"])
        self.assertEqual(resolve(url).func, views.edit_study)

    def test_qc_study_url(self):
        url = reverse(constants.url_name_for_qc_study, args=["teststudy"])
        self.assertEqual(resolve(url).func, views.qc_study)

    def test_study_details_url(self):
        url = reverse(constants.url_name_for_details, args=["teststudy"])
        self.assertEqual(resolve(url).func, views.study_details)

    def test_delete_survey_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_delete_survey)).func, views.delete_survey)

    def test_delete_question_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_delete_question)).func, views.create_survey)

    def test_create_survey_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_create_survey)).func, views.create_survey)

    def test_create_survey_id_url(self):
        url = reverse(constants.url_name_for_create_survey, args=[1])
        self.assertEqual(resolve(url).func, views.create_survey)

    def test_manage_question_url(self):
        url = reverse(constants.url_name_for_manage_question, args=[1, 1])
        self.assertEqual(resolve(url).func, views.manage_question)

    def test_create_categories_url(self):
        url = reverse(constants.url_name_for_create_categories, args=[1])
        self.assertEqual(resolve(url).func, views.manage_category_for_survey)

    def test_duplicate_survey_url(self):
        url = reverse(constants.url_name_for_duplicate_survey, args=[1])
        self.assertEqual(resolve(url).func, views.duplicate_survey)

    def test_duplicate_question_url(self):
        url = reverse(constants.url_name_for_duplicate_question, args=[1, 1])
        self.assertEqual(resolve(url).func, views.duplicate_question)

    def test_edit_survey_url(self):
        url = reverse(constants.url_name_for_edit_survey, args=["teststudy"])
        self.assertEqual(resolve(url).func, views.edit_survey)

    def test_survey_list_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_survey)).func, views.survey_list)

    def test_close_url(self):
        url = reverse(constants.url_name_for_close, args=["teststudy"])
        self.assertEqual(resolve(url).func, views.close)

    def test_download_dataset_url(self):
        url = reverse(constants.url_name_for_download_dataset, args=["samplearg"])
        self.assertEqual(resolve(url).func, views.download_dataset_from_link)

    def test_download_json_url(self):
        url = reverse(constants.url_name_for_download_json, args=[1])
        self.assertEqual(resolve(url).func, views.download_survey_json)

    def test_download_unused_files_url(self):
        url = reverse(constants.url_name_for_download, args=["samplearg"])
        self.assertEqual(resolve(url).func, views.download_unused_files)

    def test_list_of_studies_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_list_of_studies)).func, views.studies_list)

    def test_analytics_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_analytics)).func, views.analytics)

    def test_analytics_with_study_url(self):
        url = reverse(constants.url_name_for_analytics, args=["teststudy"])
        self.assertEqual(resolve(url).func, views.analytics)

    def test_delete_subject_data_url(self):
        self.assertEqual(resolve(reverse(constants.url_name_for_delete_subject_data)).func, views.delete_subject_data)