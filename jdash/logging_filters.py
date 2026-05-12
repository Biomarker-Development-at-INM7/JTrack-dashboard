import logging
import threading

# Thread-local storage for current request
_local = threading.local()

def set_request(request):
    _local.request = request

def get_request():
    return getattr(_local, 'request', None)

class UsernameLoggingFilter(logging.Filter):
    def filter(self, record):
        request = get_request()
        if request and request.user.is_authenticated:
            record.username = request.user.username
        else:
            record.username = 'Anonymous'
        return True
