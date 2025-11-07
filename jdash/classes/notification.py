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
from django.template.loader import render_to_string
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from jdash.classes.dbutils import add_verification_code
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jdash.apps import constants as constants
from jdash.apps import jdashConfig as config
logger = logging.getLogger("django")

# Ensure the token is valid and refresh if needed
def get_access_token(credentials):
    if not credentials.valid:
        credentials.refresh(Request())
    return credentials.token


def send_push_notification(title, text, receivers, study_id):
    logger.info("send_push_notification")
    sending_errors = []
    android_receivers = [] 
    apple_receivers =[]
    
    # get the receivers and split by modalities
    for receiver in receivers:
        selected_subject = receiver.split(constants.value_sep)[0]
        subject_id_with_modality = selected_subject.split(constants.sep)
        filename = study_id + '_' + subject_id_with_modality[0] + '.json'
        receiver_json_path = os.path.join(config.users_folder, filename)
        with open(receiver_json_path, 'r') as f:
            receiver_json = json.load(f)

        model = receiver_json["deviceBrand"] if "deviceBrand" in receiver_json else receiver_json["deviceBrand_ema"]
        if subject_id_with_modality[1] == constants.main:
            # Authenticate with the service account
            credentials = service_account.Credentials.from_service_account_file(
                config.SERVICE_ACCOUNT_FILE_main, scopes=config.SCOPES)

            # Generate the OAuth 2.0 Bearer token
            access_token = get_access_token(credentials)
            if model == "no auth" or model == "Android":
                headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': config.firebase_content_type}
                tokens, errors = get_receivers_tokens(subject_id_with_modality[0], study_id, subject_id_with_modality[1])   
                error  = push_notification(title, text,
                                           tokens,headers,"android",
                                           subject_id_with_modality[0],config.firebase_url_main)
            else:
                headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': config.firebase_content_type}
                tokens , errors= get_receivers_tokens(subject_id_with_modality[0], study_id, subject_id_with_modality[1])  
                error  = push_notification(title, text, tokens,headers,"apple",
                                           subject_id_with_modality[0],config.firebase_url_main)
        else:
            # Authenticate with the service account
            credentials = service_account.Credentials.from_service_account_file(
                config.SERVICE_ACCOUNT_FILE_ema, scopes=config.SCOPES)

            # Generate the OAuth 2.0 Bearer token
            access_token = get_access_token(credentials)
            headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': config.firebase_content_type}
            tokens , errors= get_receivers_tokens(subject_id_with_modality[0], study_id, subject_id_with_modality[1])
            error  = push_notification(title, text, tokens,headers,model,
                                       subject_id_with_modality[0],config.firebase_url_ema)

        sending_errors.append(error)
    logger.info(sending_errors)
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


def send_email(fullname,receiver_email,message,link):
    if "https" in link:
        subject = 'Download Link'
        body = render_to_string(constants.download_link, {'download_link': link})
    elif "confirm" in link:
        subject = 'Verify your identity'
        code = generate_verification_code()
        body = render_to_string(constants.code_verification, {'code': code})
        add_verification_code(code,message)
    elif link == "delete_subject":
        subject = "Delete Data Request"
        body = f"Request to delete subject with ID {fullname}"
        body = body + f"email address to contact {receiver_email}" 
        receiver_email = config.support_email_g
    else:
        subject =  f"Contact Us Submission from {fullname}"     
        body = f'Hello Team, '  
        body = body + "\n"+ message   
        body = body + "Please respond to this inquiry at your earliest convenience."  
        receiver_email = config.support_email_g 
    # Setup the MIME
    message = MIMEMultipart()
    message['To'] = config.support_email_g
    message['From'] = config.support_email
    message['Subject'] = subject
    message.attach(MIMEText(body, 'html'))
    # Try to log in to server and send email
    try:
        session = smtplib.SMTP(config.smtp_server,config.port)
        #session.connect(config.smtp_server, config.smtp_port)  # Explicitly connect, usually not necessary
        session.starttls(context=ssl.create_default_context()) # Secure the connection
        session.login(config.support_email, config.support_pwd)  # Login with mail_id and password
        text = message.as_string()
        session.sendmail(config.support_email,receiver_email, text)
        session.quit()
        logger.info('Mail Sent Successfully ')
        return True
    except Exception as e:
        # Print any error messages to stdout
        logger.info(f"An error occurred: {e}")
        return False
