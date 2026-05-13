from jdash.views.core_views import (
    contact_email,
    csrf_failure,
    index,
    login_request,
    logout_request,
    server_error,
    session_check,
)
from jdash.views.study_views import (
    add_study,
    close,
    download_dataset_from_link,
    edit_study,
    qc_study,
    study_audit,
    study_details,
)
from jdash.views.subject_views import (
    delete_subject_data,
    download_unused_files,
)
from jdash.views.survey_views import (
    create_survey,
    delete_survey,
    download_survey_json,
    duplicate_question,
    duplicate_survey,
    edit_survey,
    manage_category_for_survey,
    manage_question,
    survey_audit,
    survey_list,
)
from jdash.views.analytics_views import analytics
