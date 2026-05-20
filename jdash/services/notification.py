###########################################################################
####               notification.py
####           this file contains all the service methods related to studies
####           initial version written by mstolz
####           modified by mnarava
####
####
###########################################################################

import json,os,logging, random
import smtplib, ssl
import requests
from django.conf import settings
from django.template.loader import render_to_string
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from jdash.repositories.study_repository import add_verification_code
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jdash.config import constants as constants
from jdash.config import runtime_config as config
logger = logging.getLogger("django")

# Ensure the token is valid and refresh if needed
def get_access_token(credentials):
    if not credentials.valid:
        credentials.refresh(Request())
    return credentials.token


def send_push_notification(title, text, receivers, study_id):
    logger.info("send_push_notification")
    sending_errors = []

    for receiver in receivers:
        try:
            selected_subject = receiver.split(constants.value_sep)[0]
            subject_id_with_modality = selected_subject.split(constants.sep)
            if len(subject_id_with_modality) < 2:
                logger.error(f"Receiver '{receiver}' does not contain separator '{constants.sep}'")
                continue

            subject_id, modality = subject_id_with_modality
            filename = f"{study_id}_{subject_id}.json"
            receiver_json_path = os.path.join(config.users_folder, filename)

            with open(receiver_json_path, 'r') as f:
                receiver_json = json.load(f)

            model = receiver_json.get("deviceBrand") or receiver_json.get("deviceBrand_ema")
            logger.info("Model detected: %s", model)

            # Determine service account and Firebase URL based on modality
            if modality == constants.main:
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

            tokens, errors = get_receivers_tokens(subject_id, study_id, modality)
            device_type = "apple" if model != "no auth" and model != "Android" else "android"

            error = push_notification(
                title, text, tokens, headers, device_type,
                subject_id, firebase_url
            )

            sending_errors.append(error)

        except Exception as e:
            logger.exception(f"Error sending notification to {receiver}")
            sending_errors.append(str(e))

    logger.info("Notification sending errors: %s", sending_errors)
    return sending_errors

def push_notification(title, text, tokens_auth,headers,deviceBrand, ids,url):
    body = {
        'message':{
        'notification': {
            'title': title,
            'body': text
        },
        'token': tokens_auth
        }
    }

    x = requests.post(url, headers= headers,json=body)
    return x.text + ids + " with brand " + deviceBrand + "header" +str(headers)




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

