###########################################################################
####               notification.py
####           this file contains all the service methods related to studies
####           initial version written by mstolz
####           modified by mnarava
####
####
###########################################################################

import json, os, logging, random, secrets
from datetime import timedelta
import smtplib, ssl
import requests
from django.contrib.auth.hashers import make_password
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from jdash.repositories.study_repository import add_verification_code
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jdash.config import constants as constants
from jdash.config import runtime_config as config
logger = logging.getLogger("django")



def is_ios_device(device_brand):
    """Return whether a recorded device brand identifies an Apple/iOS device."""
    normalized = str(device_brand or "").strip().lower()
    return any(marker in normalized for marker in ("ios", "apple" ))

# Ensure the token is valid and refresh if needed
def get_access_token(credentials):
    if not credentials.valid:
        credentials.refresh(Request())
    return credentials.token


def send_push_notification(title, text, receivers, study_id, include_results=False):
    logger.info("send_push_notification")
    sending_errors = []
    delivery_results = []

    for receiver in receivers:
        subject_id = str(receiver)
        modality = ""
        try:
            selected_subject = receiver.split(constants.value_sep)[0]
            subject_id_with_modality = selected_subject.split(constants.sep)
            if len(subject_id_with_modality) < 2:
                error = f"Receiver '{receiver}' does not contain separator '{constants.sep}'"
                logger.error(error)
                sending_errors.append(error)
                delivery_results.append({
                    "subject_id": subject_id,
                    "modality": modality,
                    "message_id": "",
                    "success": False,
                })
                continue

            subject_id, modality = subject_id_with_modality
            filename = f"{study_id}_{subject_id}.json"
            receiver_json_path = os.path.join(config.users_folder, filename)

            with open(receiver_json_path, 'r') as f:
                receiver_json = json.load(f)

            model = (
                receiver_json.get("deviceBrand")
                if modality == constants.main
                else receiver_json.get("deviceBrand_ema")
            )
            logger.info("Model detected: %s", model)
            device_type = "apple" if is_ios_device(model) else "android"

            # Determine service account and Firebase URL based on modality
            if modality == constants.main:
                if device_type == "apple":
                    credentials_path = settings.SERVICE_ACCOUNT_FILE_MAIN_IOS
                    firebase_url = settings.FIREBASE_URL_MAIN_IOS
                else:
                    credentials_path = settings.SERVICE_ACCOUNT_FILE_MAIN
                    firebase_url = settings.FIREBASE_URL_MAIN
            else:
                credentials_path = settings.SERVICE_ACCOUNT_FILE_EMA
                firebase_url = settings.FIREBASE_URL_EMA
            
            if not credentials_path or not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Firebase service account file not found for modality={modality}: {credentials_path!r}"
                )

            credentials = service_account.Credentials.from_service_account_file(
                credentials_path, scopes=config.SCOPES)
            access_token = get_access_token(credentials)

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': config.firebase_content_type
            }

            token, token_errors = get_receivers_tokens(subject_id, study_id, modality)
            if token_errors:
                for token_error in token_errors:
                    logger.error(
                        "Push notification token error: subject=%s modality=%s platform=%s error=%s",
                        subject_id,
                        modality,
                        device_type,
                        token_error,
                    )
                sending_errors.extend(token_errors)
                delivery_results.append({
                    "subject_id": subject_id,
                    "modality": modality,
                    "message_id": "",
                    "success": False,
                })
                continue

            if include_results:
                error, message_id = push_notification(
                    title, text, token, headers, device_type,
                    subject_id, firebase_url, return_message_id=True,
                )
            else:
                error = push_notification(
                    title, text, token, headers, device_type,
                    subject_id, firebase_url,
                )
                message_id = ""

            if error:
                sending_errors.append(error)
            delivery_results.append({
                "subject_id": subject_id,
                "modality": modality,
                "message_id": message_id,
                "success": not bool(error),
            })

        except Exception as e:
            logger.exception(f"Error sending notification to {receiver}")
            sending_errors.append(str(e))
            delivery_results.append({
                "subject_id": subject_id,
                "modality": modality,
                "message_id": "",
                "success": False,
            })

    logger.info("Notification sending completed error_count=%s", len(sending_errors))
    logger.debug("Notification sending errors=%s", sending_errors)
    if include_results:
        return sending_errors, delivery_results
    return sending_errors

def push_notification(
    title,
    text,
    tokens_auth,
    headers,
    deviceBrand,
    ids,
    url,
    return_message_id=False,
):
    body = {
        'message':{
        'notification': {
            'title': title,
            'body': text
        },
        'token': tokens_auth
        }
    }

    response = requests.post(url, headers=headers, json=body, timeout=30)
    response_body = response.text.strip()

    if 200 <= response.status_code < 300:
        message_id = ""
        try:
            response_data = json.loads(response_body) if response_body else {}
            message_name = str(response_data.get("name", ""))
            message_id = message_name.rsplit("/", 1)[-1] if message_name else ""
        except (TypeError, ValueError):
            logger.warning("Could not parse notification response for subject=%s", ids)
        logger.info(
            "Push notification sent subject=%s platform=%s status=%s message_id=%s",
            ids,
            deviceBrand,
            response.status_code,
            message_id,
        )
        logger.debug("Push notification response_body=%s", response_body)
        if return_message_id:
            return None, message_id
        return None

    error = (
        f"Push notification failed for {ids} ({deviceBrand}): "
        f"HTTP {response.status_code} - {response_body}"
    )
    logger.error(error)
    if return_message_id:
        return error, ""
    return error




def get_receivers_tokens(receivers, study_id, modality):
    tokens = []

    errors = []

    token = ""
    receiver_json_path = os.path.join(config.users_folder, study_id + '_' + receivers + '.json')
    with open(receiver_json_path, 'r') as f:
        receiver_json = json.load(f)

    if modality == constants.main and 'pushNotification_token' in receiver_json:
        token = receiver_json['pushNotification_token']
        tokens.append(token)
    elif modality == constants.ema and ('pushNotification_token_ema' in receiver_json or 'pushNotification_token' in receiver_json):
        token = receiver_json['pushNotification_token_ema'] if 'pushNotification_token_ema' in receiver_json else receiver_json['pushNotification_token']
        tokens.append(token)  
    else:
            errors.append("Missing Token error : " + receivers + constants.sep + modality + " found!")
    return  token, errors


def generate_verification_code():
    """Generate a 6-digit verification code."""
    return random.randint(100000, 999999)

def send_email(fullname,receiver_email,arg,link):
 
   
    if "https" in link:
        subject = 'Download Link'
        body = render_to_string(constants.download_link, {'download_link': link})
    elif "confirm" in link:
        subject = 'Verify your identity'
        code = generate_verification_code()
        body = render_to_string(constants.code_verification, {'code': code})
        add_verification_code(code,arg)
    elif link == "delete_subject":
        subject = "Delete Data Request"
        body = f"Request to delete subject with ID {fullname}"
        body = body + f"email address to contact {receiver_email}" 
        receiver_email = settings.SUPPORT_EMAIL_G
    else:
        subject =  f"Contact Us Submission from {fullname}"     
        body = f'Hello Team, '  
        body = body + "\n"+ arg
        body = body + "Please respond to this inquiry at your earliest convenience."  
        receiver_email = settings.SUPPORT_EMAIL_G 
       

    message = MIMEMultipart()
    message.attach(MIMEText(body, 'html'))
    message['Subject'] = subject
    message['To'] = receiver_email
    message['From'] = settings.SUPPORT_EMAIL
    
    # Try to log in to server and send email
    try:
        session = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        #session.connect(settings.SMTP_SERVER, settings.SMTP_PORT)  # Explicitly connect, usually not necessary
        session.starttls(context=ssl.create_default_context()) # Secure the connection
        session.login(settings.SUPPORT_EMAIL, settings.SUPPORT_PWD)  # Login with mail_id and password
        text = message.as_string()
        session.sendmail(settings.SUPPORT_EMAIL, receiver_email, text)
        session.quit()
        logger.debug('send_email::Email sent successfully to %s', receiver_email)
        logger.info('Mail Sent Successfully ')
        return True
    except Exception as e:
        # Print any error messages to stdout
        logger.info(f"An error occurred: {e}")
        return False

def send_qc_comment_email(study_name, testcase_id, description, comment_text, username, timestamp):
    """Send an email when a QC comment is added from the QC modal."""
    subject = f"QC Comment Added: {study_name}"
    body = (
        "<p>A new QC comment was added.</p>"
        f"<p><strong>Study:</strong> {study_name}</p>"
        f"<p><strong>Test case:</strong> {testcase_id}</p>"
        f"<p><strong>Description:</strong> {description}</p>"
        f"<p><strong>User:</strong> {username}</p>"
        f"<p><strong>Timestamp:</strong> {timestamp}</p>"
        f"<p><strong>Comment:</strong><br>{comment_text}</p>"
    )

    message = MIMEMultipart()
    message.attach(MIMEText(body, "html"))
    message["Subject"] = subject
    message["To"] = settings.SUPPORT_EMAIL_G
    message["From"] = settings.SUPPORT_EMAIL

    try:
        session = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        session.starttls(context=ssl.create_default_context())
        session.login(settings.SUPPORT_EMAIL, settings.SUPPORT_PWD)
        session.sendmail(settings.SUPPORT_EMAIL, settings.SUPPORT_EMAIL_G, message.as_string())
        session.quit()
        logger.info("QC comment email sent for study=%s testcase=%s", study_name, testcase_id)
        return True
    except Exception as exc:
        logger.info("QC comment email failed for study=%s testcase=%s error=%s", study_name, testcase_id, exc)
        return False
