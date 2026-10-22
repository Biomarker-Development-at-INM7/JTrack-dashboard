from django.conf import settings

from jdash.logging_filters import set_request


class ScriptPrefixPathInfoMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        script_name = (getattr(settings, "FORCE_SCRIPT_NAME", "") or "").rstrip("/")
        if script_name:
            path_info = request.path_info
            if path_info == script_name:
                request.path_info = "/"
            elif path_info.startswith(f"{script_name}/"):
                request.path_info = path_info[len(script_name):] or "/"

            if request.path_info != path_info:
                request.META["PATH_INFO"] = request.path_info
                request.path = f"{script_name}{request.path_info}"

        return self.get_response(request)


class ThreadLocalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_request(request)
        response = self.get_response(request)
        return response
