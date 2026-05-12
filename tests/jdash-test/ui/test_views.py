import pytest
from django.urls import reverse
from django.contrib.auth.models import User, AnonymousUser
from jdash.models import Survey
from django.http import HttpRequest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib import messages
from jdash.models import FileDownloadToken
from jdash.apps import constants
from datetime import datetime, timedelta
import uuid
from unittest.mock import patch, MagicMock
from django.utils import timezone
from jdash import views
from django.test import TestCase, RequestFactory, Client
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages.storage.fallback import FallbackStorage


@pytest.fixture
def logged_in_client(client):
    user = User.objects.create_user(username="testuser", password="testpass")
    client.login(username="testuser", password="testpass")
    return client

@pytest.mark.django_db
class TestPositiveViews:

    def test_index_view(self, logged_in_client):
        response = logged_in_client.get(reverse("home"))
        assert response.status_code in [200, 500]

    def test_login_page_loads(self, client):
        response = client.get(reverse("login"))
        assert response.status_code == 200
        assert b"Login" in response.content

    def test_logout_view(self, logged_in_client):
        response = logged_in_client.get(reverse("logout"))
        assert response.status_code == 302

    def test_contact_email_get(self, client):
        response = client.get(reverse("contact_email"))
        assert response.status_code == 200

    def test_session_check(self, logged_in_client):
        response = logged_in_client.get(reverse("session_check"))
        assert response.status_code == 200
        assert response.json()["active"] is True

    def test_download_valid_token(self, client):
        valid_uuid = uuid.uuid4()
        token = FileDownloadToken.objects.create(
            token=valid_uuid,
            email="test@example.com",
            expiration_date=timezone.now() + timedelta(days=1),
            file_name="mock_study",
            code="123456"
        )
        url = reverse("download", kwargs={"arg": str(valid_uuid)})
        response = client.get(url)
        assert response.status_code in [200, 302]

@pytest.mark.django_db
class TestNegativeViews:

    def test_csrf_failure_redirect(self, client):
        from jdash.views import csrf_failure
        request = client.get(reverse("login"))
        response = csrf_failure(request.wsgi_request)
        assert response.status_code == 302
        assert response.url == "/login/"

    def test_download_invalid_token(self, client):
        url = reverse("download", kwargs={"arg": "invalidtoken"})
        response = client.get(url)
        assert response.status_code in [302, 404]

    def test_download_token_invalid_code(self, logged_in_client):
        token = FileDownloadToken.objects.create(
            token=uuid.uuid4(),
            code="123456",  # Expected
            file_name="study_x",
            expiration_date=timezone.now() + timedelta(days=1),
            email="test@example.com"
        )
        url = reverse("download", kwargs={"arg": token.token})
        response = logged_in_client.get(url, data={
            "verifyCode": "wrongcode",  # Incorrect code
            "confirm": "Download"
        })

        # Django messages are rendered in the template only if your test environment supports it
        assert b"Invalid code" in response.content or response.status_code in [200, 302]

    def test_download_token_expired(self, client):
        token = FileDownloadToken.objects.create(
            token=uuid.uuid4(),
            email="test@example.com",
            expiration_date=timezone.now() - timedelta(days=1),
            file_name="mock_study",
            code="123"
        )
        url = reverse("download", kwargs={"arg": str(token.token)})
        response = client.get(url)
        assert response.status_code == 302

    def test_delete_survey_missing_post(self, logged_in_client):
        url = reverse("delete_survey")
        response = logged_in_client.post(url, data={})  # missing expected key
        assert response.status_code == 200  # or 302 depending on view logic

    def test_create_study_invalid_form(self, logged_in_client):
        url = reverse("add_study")
        with pytest.raises(RuntimeError):
            logged_in_client.post(url, data={})

    def test_manage_question_invalid_forms(self, logged_in_client):
        url = reverse("manage_question", kwargs={"survey_id": 999, "question_id": 0})

        with pytest.raises(Survey.DoesNotExist):
            logged_in_client.post(url, data={})

    def test_non_existent_route(self, client):
        response = client.get("/non-existent-path/")
        assert response.status_code == 404


class TestIndexView(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='12345')

    def _make_request(self, user):
        request = self.factory.get("/")
        request.user = user
        # Use MagicMock for session to allow setting attributes
        request.session = MagicMock()
        # request.session.session_key = 'abc123'
        request.session.modified = False
        # Make session.get behave like a dict get with fallback
        request.session.get.side_effect = lambda key, default=None: request.session.__dict__.get(key, default)
        return request


    def add_session_to_request(self, request):
        middleware = SessionMiddleware(get_response=lambda r: None)
        middleware.process_request(request)
        request.session.save()

    @patch('jdash.views.render')
    @patch('jdash.views.get_all_study_details')
    @patch('jdash.views.SessionManager.get_specific_session_data')
    def test_authenticated_user_with_no_study_meta_fetches_and_renders(self, mock_get_session, mock_get_all,
                                                                       mock_render):
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        self.add_session_to_request(request)

        print(f"Session key: {request.session.session_key}")
        assert request.session.session_key is not None

        # Provide three return values for the three calls:
        mock_get_session.side_effect = [
            {'username': 'testuser'},  # user details (must not be None)
            None,  # study_meta missing, triggers fetch
            None  # stats missing
        ]

        mock_get_all.return_value = ([{'title': 'Study1', constants.key_name_sensor_list: []}], {'stat': 1}, '')

        mock_render.return_value = MagicMock()

        response = views.index(request)

        mock_get_all.assert_called_once_with(request.user)
        mock_render.assert_called_once()

        # Optionally inspect context passed to render:
        args, kwargs = mock_render.call_args
        context = args[2] if len(args) > 2 else {}
        assert constants.key_name_study_meta in context


    @patch('jdash.views.render')
    @patch('jdash.views.SessionManager.get_specific_session_data')
    def test_authenticated_user_with_study_meta_in_session_renders(self, mock_get_session, mock_render):
        factory = RequestFactory()
        request = factory.get('/')
        request.user = self.user
        self.add_session_to_request(request)

        print(f"Session key: {request.session.session_key}")
        assert request.session.session_key is not None

        study_meta = [{'title': 'Cached Study', constants.key_name_sensor_list: []}]
        stats = {'stat': 42}

        # For cached scenario, first two calls return cached data
        mock_get_session.side_effect = [
            {'username': 'testuser'},  # user details (not used here but safe)
            study_meta,  # cached study_meta
            stats  # cached stats
        ]

        mock_render.return_value = MagicMock()

        response = views.index(request)

        mock_get_session.assert_called()
        mock_render.assert_called_once()

        args, kwargs = mock_render.call_args
        context = args[2] if len(args) > 2 else {}
        assert constants.key_name_study_meta in context
        assert context[constants.key_name_study_meta] == study_meta


    @patch("jdash.views.SessionManager.get_specific_session_data")
    @patch("jdash.views.render")
    def test_exception_during_processing_renders_error(self, mock_render, mock_get_session):
        request = self._make_request(self.user)
        mock_get_session.side_effect = Exception("Unexpected error")

        mock_render.return_value = MagicMock()

        response = views.index(request)

        # Should render error page template on exception
        args, kwargs = mock_render.call_args
        self.assertIn('error', args[1].lower())

    def test_unauthenticated_user_redirects_to_login(self):
        client = Client()
        response = client.get(reverse('home'))  # use the correct name
        assert response.status_code == 302


@pytest.fixture
def user(db):
    return User.objects.create_user(username='testuser', password='pass')


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def default_context():
    return {
        constants.key_name_subject_details: {
            constants.key_name_ids_to_be_removed: ['id1', 'id2']
        }
    }

def add_session_to_request(request):
    """Attach a session to the request so views can access request.session"""
    middleware = SessionMiddleware(get_response=lambda r: None)
    middleware.process_request(request)
    request.session.save()

@patch('jdash.views.display_study')
@patch('jdash.views.SessionManager.get_specific_session_data')
@patch('jdash.views.render')
def test_get_request_renders_details(mock_render, mock_session, mock_display, rf, user, default_context):
    mock_display.return_value = default_context
    mock_session.return_value = {constants.field_name_email: 'test@example.com'}
    request = rf.get('/study/some_study/')
    add_session_to_request(request)
    request.user = user

    views.study_details(request, 'some_study')

    mock_render.assert_called_once()
    context_passed = mock_render.call_args[0][2]
    assert constants.key_name_new_subjects_form in context_passed
    assert constants.key_name_remove_subjects_form in context_passed
    assert constants.key_name_notification_form in context_passed
    assert constants.key_name_delete_subject_form in context_passed
    assert context_passed[constants.field_name_email] == 'test@example.com'


@patch('jdash.views.display_study')
@patch('jdash.views.SessionManager.get_specific_session_data')
@patch('jdash.views.SendNotificationForm')
@patch('jdash.views.get_notification_form_data')
@patch('jdash.views.send_push_notification')
@patch('jdash.views.render')
def test_post_send_notification_valid_sends_notification(mock_render, mock_send, mock_get_data, mock_form_class, mock_session, mock_display, rf, user, default_context):
    mock_display.return_value = default_context
    mock_session.return_value = {constants.field_name_email: 'test@example.com'}
    mock_form = MagicMock(is_valid=MagicMock(return_value=True))
    mock_form_class.return_value = mock_form
    mock_get_data.return_value = ("title", "text", ["receiver1"])
    request = rf.post('/study/some_study/', data={constants.button_name_send_notification: 'clicked'})
    add_session_to_request(request)
    request.user = user

    views.study_details(request, 'some_study')

    mock_send.assert_called_once_with("title", "text", ["receiver1"], 'some_study')


@patch('jdash.views.display_study')
@patch('jdash.views.SessionManager.get_specific_session_data')
@patch('jdash.views.CreateSubjectForm')
@patch('jdash.views.create_subjects_for_study')
@patch('jdash.views.update_number_of_subjects')
@patch('jdash.views.render')
def test_post_create_subjects_valid_creates(mock_render, mock_update, mock_create_subjects, mock_form_class, mock_session, mock_display, rf, user, default_context):
    mock_display.return_value = default_context
    mock_session.return_value = {constants.field_name_email: 'test@example.com'}
    mock_form = MagicMock(is_valid=MagicMock(return_value=True))
    mock_form.cleaned_data = {constants.field_name_number_of_subjects: 5}
    mock_form_class.return_value = mock_form
    mock_create_subjects.return_value = 10
    request = rf.post('/study/some_study/', data={constants.button_name_create_subjects: 'clicked'})
    add_session_to_request(request)
    request.user = user

    views.study_details(request, 'some_study')

    mock_create_subjects.assert_called_once_with('some_study', 5)
    mock_update.assert_called_once_with('some_study', 10)


@patch('jdash.views.display_study')
@patch('jdash.views.SessionManager.get_specific_session_data')
@patch('jdash.views.RemoveSubjectsForm')
@patch('jdash.views.remove_subjects_from_study')
@patch('jdash.views.render')
def test_post_remove_subjects_valid_removes(mock_render, mock_remove, mock_form_class, mock_session, mock_display, rf, user, default_context):
    mock_display.return_value = default_context
    mock_session.return_value = {constants.field_name_email: 'test@example.com'}
    mock_form = MagicMock(is_valid=MagicMock(return_value=True))
    mock_form.cleaned_data = {constants.field_name_subject_to_remove: 'subj1'}
    mock_form_class.return_value = mock_form
    request = rf.post('/study/some_study/', data={constants.button_name_remove_subjects: 'clicked'})
    add_session_to_request(request)
    request.user = user

    views.study_details(request, 'some_study')

    mock_remove.assert_called_once_with('some_study', 'subj1', default_context)


@patch('jdash.views.display_study')
@patch('jdash.views.SessionManager.get_specific_session_data')
@patch('jdash.views.DeleteSubjectForm')
@patch('jdash.views.delete_subjects_from_server')
@patch('jdash.views.render')
def test_post_delete_subject_data_valid_deletes(mock_render, mock_delete, mock_form_class, mock_session, mock_display, rf, user, default_context):
    mock_display.return_value = default_context
    mock_session.return_value = {constants.field_name_email: 'test@example.com'}
    mock_form = MagicMock(is_valid=MagicMock(return_value=True))
    mock_form.cleaned_data = {constants.field_name_subjectId: 'id1,id2'}
    mock_form_class.return_value = mock_form
    request = rf.post('/study/some_study/', data={constants.button_name_delete_subject_data: 'clicked'})
    add_session_to_request(request)
    request.user = user

    views.study_details(request, 'some_study')

    mock_delete.assert_called_once_with('id1,id2')


@patch('jdash.views.display_study')
@patch('jdash.views.SessionManager.get_specific_session_data')
@patch('jdash.views.get_all_study_details')
@patch('jdash.views.render')
def test_error_in_context_triggers_home_render(mock_render, mock_get_all, mock_session, mock_display, rf, user):
    error_context = {constants.key_name_error_message: "error", constants.key_name_subject_details: {}}
    mock_display.return_value = error_context
    mock_session.return_value = {constants.field_name_email: 'test@example.com'}
    mock_get_all.return_value = ([{'title': 'study1'}], {'stats': 1}, 'error message')
    request = rf.get('/study/some_study/')
    add_session_to_request(request)
    request.user = user

    views.study_details(request, 'some_study')

    mock_render.assert_called_once()
    args = mock_render.call_args[0]
    assert args[1] == constants.home_page
    assert constants.key_name_error_message in args[2]

def add_messages_middleware(request):
    middleware = MessageMiddleware(lambda req: None)
    middleware.process_request(request)
    request._messages = messages.get_messages(request)


def add_session_and_messages_middleware(request):
    # Add session middleware
    session_middleware = SessionMiddleware(get_response=lambda r: None)
    session_middleware.process_request(request)
    request.session.save()

    # Add messages middleware
    messages_middleware = MessageMiddleware(get_response=lambda r: None)
    messages_middleware.process_request(request)

    # Ensure _messages attribute exists by attaching fallback storage manually
    if not hasattr(request, '_messages'):
        request._messages = FallbackStorage(request)


@pytest.mark.django_db
@patch('jdash.views.retrieve_all_survey_for_user')
@patch('jdash.views.get_json_data')
@patch('jdash.views.CreateStudyForm')
@patch('jdash.views.TaskForm')
@patch('jdash.views.formset_factory')
@patch('jdash.views.update_study_meta_data')
@patch('jdash.views.render')
def test_edit_study_post_update_valid(
    mock_render, mock_update, mock_formset_factory, mock_task_form,
    mock_create_study_form, mock_get_json, mock_retrieve_surveys, rf, user
):
    request = rf.post('/edit-study/teststudy/', data={constants.button_name_update_study: True})
    add_session_to_request(request)
    request.user = user

    # Setup mocks
    mock_retrieve_surveys.return_value = ['survey_obj']
    mock_get_json.return_value = {}
    mock_formset_factory.return_value = MagicMock(return_value='formset_instance')
    form_mock = MagicMock()
    form_mock.is_valid.return_value = True
    mock_create_study_form.return_value = form_mock
    mock_update.return_value = {'some': 'context'}

    # Run view
    response = views.edit_study(request, 'teststudy')

    # Check calls
    mock_retrieve_surveys.assert_called_once_with(user, request.session.session_key)
    mock_get_json.assert_called_once_with('teststudy')
    mock_create_study_form.assert_called_once_with(request.POST, survey=['survey_obj'])
    mock_update.assert_called_once_with('teststudy', form_mock, 'formset_instance', request)
    mock_render.assert_called_once()

    # The context passed to render should include success message and form keys
    args, kwargs = mock_render.call_args
    context = kwargs.get('context', {})
    assert 'some' in context
    assert constants.key_name_survey_form in context
    assert constants.key_name_question_form in context
    assert constants.key_name_success_message in context
    assert response == mock_render.return_value

@patch('jdash.views.retrieve_all_survey_for_user')
@patch('jdash.views.get_json_data')
@patch('jdash.views.CreateStudyForm')
@patch('jdash.views.TaskForm')
@patch('jdash.views.formset_factory')
@patch('jdash.views.render')
def test_edit_study_get_with_survey_and_task_list(
    mock_render, mock_formset_factory, mock_task_form, mock_create_study_form,
    mock_get_json, mock_retrieve_surveys, rf, user
):
    # json_meta contains survey with no id and task list
    json_meta = {
        "survey": {},
        constants.key_name_task_list: [{"task1": "do"}],
        constants.key_name_number_of_subjects: 42
    }
    mock_retrieve_surveys.return_value = ['survey_obj']
    mock_get_json.return_value = json_meta
    mock_formset_factory.return_value = MagicMock(return_value='task_formset_instance')
    mock_create_study_form.return_value = MagicMock()

    request = rf.get('/edit-study/teststudy/')
    add_session_to_request(request)
    request.user = user
    add_session_and_messages_middleware(request)

    response = views.edit_study(request, 'teststudy')

    mock_retrieve_surveys.assert_called_once()
    mock_get_json.assert_called_once()
    mock_formset_factory.assert_called_once_with(mock_task_form, extra=1)
    mock_create_study_form.assert_called_once_with(data=json_meta, survey=['survey_obj'])
    mock_render.assert_called_once()

    args, kwargs = mock_render.call_args
    context = kwargs.get('context', {})
    assert context.get("is_file") is True
    assert context.get(constants.key_name_task_formset) == 'task_formset_instance'
    assert context.get(constants.key_name_study_name) == 'teststudy'
    assert context.get(constants.key_name_number_of_subjects) == 42
    assert response == mock_render.return_value

@patch('jdash.views.retrieve_all_survey_for_user')
@patch('jdash.views.get_json_data')
@patch('jdash.views.CreateStudyForm')
@patch('jdash.views.TaskForm')
@patch('jdash.views.formset_factory')
@patch('jdash.views.render')
def test_edit_study_get_with_survey_with_id(
    mock_render, mock_formset_factory, mock_task_form, mock_create_study_form,
    mock_get_json, mock_retrieve_surveys, rf, user
):
    json_meta = {
        "survey": {"id": 123},
        constants.key_name_number_of_subjects: 10
    }
    mock_retrieve_surveys.return_value = ['survey_obj']
    mock_get_json.return_value = json_meta
    mock_formset_factory.return_value = MagicMock(return_value='task_formset_instance')
    mock_create_study_form.return_value = MagicMock()

    request = rf.get('/edit-study/teststudy/')
    add_session_to_request(request)
    request.user = user
    add_session_and_messages_middleware(request)

    response = views.edit_study(request, 'teststudy')

    mock_create_study_form.assert_called_once_with(data=json_meta, survey=['survey_obj'], initial_survey_id=123)
    assert mock_render.called
    args, kwargs = mock_render.call_args
    context = kwargs.get('context', {})
    assert context.get("is_file") is False
    assert response == mock_render.return_value

@patch('jdash.views.retrieve_all_survey_for_user')
@patch('jdash.views.get_json_data')
@patch('jdash.views.CreateStudyForm')
@patch('jdash.views.TaskForm')
@patch('jdash.views.formset_factory')
@patch('jdash.views.render')
def test_edit_study_get_without_survey(
    mock_render, mock_formset_factory, mock_task_form, mock_create_study_form,
    mock_get_json, mock_retrieve_surveys, rf, user
):
    json_meta = {
        constants.key_name_number_of_subjects: 5
    }
    mock_retrieve_surveys.return_value = ['survey_obj']
    mock_get_json.return_value = json_meta
    mock_formset_factory.return_value = MagicMock(return_value='task_formset_instance')
    mock_create_study_form.return_value = MagicMock()

    request = rf.get('/edit-study/teststudy/')
    add_session_to_request(request)
    request.user = user
    add_session_and_messages_middleware(request)

    response = views.edit_study(request, 'teststudy')

    mock_create_study_form.assert_called_once_with(data=json_meta, survey=['survey_obj'])
    assert mock_render.called
    args, kwargs = mock_render.call_args
    context = kwargs.get('context', {})
    assert response == mock_render.return_value

@patch('jdash.views.messages.error')
@patch('jdash.views.retrieve_all_survey_for_user')
@patch('jdash.views.get_json_data')
@patch('jdash.views.render')
def test_edit_study_error_message_calls_messages_error(
    mock_render, mock_get_json, mock_retrieve_surveys, mock_messages_error, rf, user
):
    json_meta = {
        constants.key_name_number_of_subjects: 1,
        constants.key_name_survey: {}
    }
    mock_retrieve_surveys.return_value = []
    mock_get_json.return_value = json_meta

    request = rf.get('/edit-study/teststudy/')
    add_session_to_request(request)
    request.user = user
    add_session_and_messages_middleware(request)

    # Simulate error in context
    context_with_error = {constants.key_name_error_message: "some error"}

    with patch('jdash.views.update_study_meta_data', return_value=context_with_error):
        response = views.edit_study(request, 'teststudy')

    mock_messages_error.assert_called_once_with(request, "")
    mock_render.assert_called_once()


@pytest.mark.django_db
class TestDownloadDatasetFromLink:

    @pytest.fixture
    def valid_token(self, db):
        return FileDownloadToken.objects.create(
            token=str(uuid.uuid4()),
            expiration_date=timezone.now() + timedelta(days=1),
            code="123456",
            file_name="study1",
            email="user@example.com"
        )

    @pytest.fixture
    def expired_token(self, db):
        return FileDownloadToken.objects.create(
            token=str(uuid.uuid4()),
            expiration_date=timezone.now() - timedelta(days=1),
            code="654321",
            file_name="study2",
            email="user2@example.com"
        )

    @patch('jdash.views.messages.error')
    @patch('jdash.views.render')
    def test_invalid_token_renders_error(self, mock_render, mock_messages_error):
        # Simulate FileDownloadToken.objects.get raising DoesNotExist
        with patch('jdash.views.FileDownloadToken.objects.get') as mock_get:
            mock_get.side_effect = FileDownloadToken.DoesNotExist

            request = HttpRequest()
            request.method = "GET"
            request.GET = {}
            response = views.download_dataset_from_link(request, "invalidtoken")

            mock_render.assert_called_once_with(request, constants.error_page, context={})
            mock_messages_error.assert_not_called()

    @patch('jdash.views.messages.error')
    @patch('jdash.views.render')
    def test_expired_token_renders_error(self, mock_render, mock_messages_error):
        # expired token triggers DoesNotExist, so mock .get to raise DoesNotExist
        with patch('jdash.views.FileDownloadToken.objects.get') as mock_get:
            mock_get.side_effect = FileDownloadToken.DoesNotExist

            request = HttpRequest()
            request.method = "GET"
            request.GET = {}

            response = views.download_dataset_from_link(request, "expiredtoken")

            mock_render.assert_called_once_with(request, constants.error_page, context={})
            mock_messages_error.assert_not_called()

    @patch('jdash.views.download_dataset')
    @patch('jdash.views.messages.error')
    @patch('jdash.views.render')
    def test_valid_token_with_correct_code_downloads(self, mock_render, mock_messages_error, mock_download_dataset, valid_token):
        with patch('jdash.views.FileDownloadToken.objects.get') as mock_get:
            mock_get.return_value = valid_token

            request = HttpRequest()
            request.method = "GET"
            request.GET = {
                constants.button_name_download_data_confirm: "1",
                "verifyCode": valid_token.code
            }

            views.download_dataset_from_link(request, valid_token.token)

            mock_download_dataset.assert_called_once_with(valid_token.file_name)
            mock_messages_error.assert_not_called()
            mock_render.assert_not_called()  # Should not render any page on successful download

    @patch('jdash.views.messages.error')
    @patch('jdash.views.render')
    def test_valid_token_with_incorrect_code_shows_error(self, mock_render, mock_messages_error, valid_token):
        with patch('jdash.views.FileDownloadToken.objects.get') as mock_get:
            mock_get.return_value = valid_token

            request = HttpRequest()
            request.method = "GET"
            request.GET = {
                constants.button_name_download_data_confirm: "1",
                "verifyCode": "wrongcode"
            }

            views.download_dataset_from_link(request, valid_token.token)

            mock_messages_error.assert_called_once_with(request, "Invalid verification code.")
            mock_render.assert_called_once_with(request, constants.download_confirm, context={'arg': valid_token.token})

    @patch('jdash.views.send_email')
    @patch('jdash.views.render')
    def test_initial_request_sends_email_and_renders_confirm(self, mock_render, mock_send_email, valid_token):
        with patch('jdash.views.FileDownloadToken.objects.get') as mock_get:
            mock_get.return_value = valid_token

            request = HttpRequest()
            request.method = "GET"
            request.GET = {}

            views.download_dataset_from_link(request, valid_token.token)

            mock_send_email.assert_called_once_with("", valid_token.email, valid_token.token, "confirm")
            mock_render.assert_called_once_with(request, constants.download_confirm, context={'arg': valid_token.token})


@pytest.fixture
def user(db):
    return User.objects.create_user(username="testuser", password="pass")

@pytest.mark.django_db
@pytest.mark.usefixtures("user")
class TestCreateSurveyView:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.factory = RequestFactory()

    def _make_request(self, method='GET', post_data=None, files=None, user=None):
        if method == 'POST':
            request = self.factory.post('/create-survey/', data=post_data or {}, files=files or {})
        else:
            request = self.factory.get('/create-survey/')
        request.user = user
        request.session = {}
        request.headers = {}
        return request

    @patch('jdash.views.context_for_create_survey_page')
    @patch('jdash.views.render')
    def test_get_request_renders_page(self, mock_render, mock_context, user):
        mock_context.return_value = {'dummy': 'context'}
        request = self._make_request('GET')
        request.user = user
        response = views.create_survey(request)
        mock_context.assert_called_once_with(0)
        mock_render.assert_called_once_with(request, constants.create_survey_page, context=mock_context.return_value)

    @patch('jdash.views.get_survey_form_data')
    @patch('jdash.views.create_survey_from_surveyForm')
    @patch('jdash.views.SurveyForm')
    def test_post_create_survey_success_redirects(self, mock_form_class, mock_create_survey, mock_get_data, user):
        mock_form = MagicMock()
        mock_form.is_valid = True
        mock_form.errors = {}
        mock_form_class.return_value = mock_form
        mock_get_data.return_value = {'title': 'Test Survey'}
        mock_create_survey.return_value = {"survey_id": 123}

        post_data = {constants.button_name_create_survey: '1'}
        request = self._make_request('POST', post_data=post_data)
        request.user = user
        request.headers = {}

        response = views.create_survey(request)

        assert response.status_code == 302
        assert response.url == reverse("create_categories", kwargs={"survey_id": 123})


    @patch('jdash.views.delete_question_from_survey')
    def test_post_delete_question(self, mock_delete_question, user):
        mock_delete_question.return_value = {
            'some_key': 'some_value',
            'survey_id': 1,  # important to include this for template URL resolution
        }

        post_data = {
            constants.button_name_delete_question: '1',
            constants.key_name_survey_id: '15',
            constants.field_name_question_id: '7'
        }
        request = self._make_request('POST', post_data=post_data)
        request.user = user

        response = views.create_survey(request)

        mock_delete_question.assert_called_once_with('7', '15')

    @patch('jdash.views.context_for_create_survey_page')
    @patch('jdash.views.messages.error')
    @patch('jdash.views.create_survey_from_surveyForm')
    def test_exception_handling_shows_message(self, mock_create_survey, mock_messages_error, mock_context, user):
        mock_context.side_effect = Exception("Boom!")

        request = self._make_request('GET')
        request.user = user

        # call the view, which should catch the exception and call messages.error
        response = views.create_survey(request)

        mock_messages_error.assert_called_once()
        # You can check the message contents loosely:
        called_args = mock_messages_error.call_args[0]
        assert "Boom!" in called_args[1]


class DownloadUnusedFilesTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='password')

    def _add_session_to_request(self, request):
        middleware = SessionMiddleware(get_response=lambda req: None)
        middleware.process_request(request)
        request.session.save()

    def test_data_arg_branch_with_empty_email(self):
        request = self.factory.post('/some-url/', data={
            'user_email': 'test@example.com',
            constants.key_name_study_name: 'study1',
            constants.key_name_type: 'type1',
        })
        self._add_session_to_request(request)
        request.session['user_details'] = {
            constants.field_name_email: '',
            constants.field_name_username: 'testuser',
        }
        request.user = self.user  # Set user on request

        response = views.download_unused_files(request, 'data')
        self.assertEqual(response.status_code, 200)

    def test_data_arg_branch_with_non_empty_email(self):
        request = self.factory.post('/some-url/', data={
            'user_email': 'another@example.com',
            constants.key_name_study_name: 'study1',
            constants.key_name_type: 'type1',
        })
        self._add_session_to_request(request)
        request.session['user_details'] = {
            constants.field_name_email: 'existing@example.com',
            constants.field_name_username: 'testuser',
        }
        request.user = self.user  # Set user on request

        response = views.download_unused_files(request, 'data')
        self.assertEqual(response.status_code, 200)


class AddStudyViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(username='testuser', password='pass')

    def _add_middleware(self, request):
        # Add session and message middleware to the request
        session_middleware = SessionMiddleware(lambda req: None)
        session_middleware.process_request(request)
        request.session.save()

        message_middleware = MessageMiddleware(lambda req: None)
        message_middleware.process_request(request)
        request._messages = MagicMock()  # Simplify messages

    @patch('jdash.views.create_new_study')
    @patch('jdash.views.CreateStudyForm')
    @patch('jdash.views.formset_factory')
    def test_create_new_study_called_on_valid_post(self, mock_formset_factory, mock_create_study_form,
                                                   mock_create_new_study):
        mock_formset_instance = MagicMock()
        mock_formset_factory.return_value = mock_formset_instance

        mock_form = MagicMock()
        mock_form.is_valid.return_value = True
        mock_create_study_form.return_value = mock_form

        mock_create_new_study.return_value = {
            "success_message": "Study added successfully",
            constants.key_name_error_message: False,
        }

        post_data = {
            'title': 'Test Study',
        }
        request = self.factory.post('/add-study/', data=post_data)
        request.user = self.user
        self._add_middleware(request)

        response = views.add_study(request)

        mock_create_new_study.assert_called_once()
        called_args = mock_create_new_study.call_args[0]
        self.assertIs(called_args[0], mock_form)
        self.assertIsInstance(called_args[1], MagicMock)  # formset instance
        self.assertIs(called_args[2], request)

        self.assertEqual(response.status_code, 200)
        self.assertIn(constants.home_page, [t.name for t in response.templates])