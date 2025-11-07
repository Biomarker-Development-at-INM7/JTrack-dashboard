# maintenance_middleware.py
from django.shortcuts import render
from django.conf import settings

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow superusers or staff to bypass (optional)
        if getattr(settings, "MAINTENANCE_MODE", False):
            if request.user.is_authenticated and not request.user.is_staff:
                return render(request, "maintenance.html", status=503)
        return self.get_response(request)
