from jdash.logging_filters import set_request

class ThreadLocalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_request(request)
        response = self.get_response(request)
        return response
