from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.db import SessionStore

class SessionManager:
    @staticmethod
    def read_session_data(session_key):
        try:
            session = Session.objects.get(session_key=session_key)
            return session.get_decoded()
        except Session.DoesNotExist:
            return None
        
    @staticmethod
    def get_specific_session_data(session_key, key, default=None):
        session_data = SessionManager.read_session_data(session_key)

        if session_data:
            return session_data.get(key)
        else:
            return default
    
    @staticmethod
    def write_session_data(session_key, key, value):

        session = SessionStore(session_key=session_key)
        session[key] = value       
        session.save()


    @staticmethod
    def delete_specific_session_valuedata(session_key, key, identifier,value):
        session = SessionStore(session_key=session_key)
        if key in session:
            for obj in session[key]:
                del obj
            session.save()

    @staticmethod
    def delete_specific_session_data(session_key, key ):
        session = SessionStore(session_key=session_key)
        if key in session:
            del session[key]
            session.save()

    @staticmethod
    def delete_entire_session(session_key):
        try:
            session = Session.objects.get(session_key=session_key)
            session.delete()
        except Session.DoesNotExist:
            pass

