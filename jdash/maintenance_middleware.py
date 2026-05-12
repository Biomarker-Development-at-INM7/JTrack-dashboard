from django.conf import settings
from django.shortcuts import render


class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def _normalize_path(self, request):
        path = request.path or ""
        script_name = (getattr(settings, "FORCE_SCRIPT_NAME", "") or "").rstrip("/")
        language_codes = {code for code, _label in getattr(settings, "LANGUAGES", [])}
        parts = [part for part in path.split("/") if part]

        variants = {path or "/"}

        if script_name and path.startswith(script_name):
            variants.add(path[len(script_name):] or "/")

        if parts and parts[0] in language_codes:
            without_lang = "/" + "/".join(parts[1:]) if parts[1:] else "/"
            variants.add(without_lang)
            if script_name and without_lang.startswith(script_name):
                variants.add(without_lang[len(script_name):] or "/")

        if script_name:
            script_part = script_name.lstrip("/")
            if parts and parts[0] == script_part:
                without_script = "/" + "/".join(parts[1:]) if parts[1:] else "/"
                variants.add(without_script)
                nested_parts = [part for part in without_script.split("/") if part]
                if nested_parts and nested_parts[0] in language_codes:
                    variants.add("/" + "/".join(nested_parts[1:]) if nested_parts[1:] else "/")

        return {variant or "/" for variant in variants}

    def _is_admin_path(self, request):
        return any(
            candidate.startswith("/admin/") or candidate == "/admin"
            for candidate in self._normalize_path(request)
        )

    def _is_exempt_path(self, request):
        candidate_paths = self._normalize_path(request)
        static_url = getattr(settings, "STATIC_URL", "/static/")
        login_url = getattr(settings, "LOGIN_URL", "/login/")
        normalized_login = login_url.rstrip("/")

        exempt_paths = {
            login_url,
            "/logout/",
            "/favicon.ico",
            "/admin",
            "/admin/",
            "/admin/login/",
        }

        return any(
            candidate in exempt_paths
            or candidate.rstrip("/").endswith(normalized_login)
            or candidate.rstrip("/").endswith("/logout")
            or candidate.startswith(static_url)
            or candidate.startswith("/static/")
            or candidate.startswith("/__reload__/")
            for candidate in candidate_paths
        )

    def _is_allowed_user(self, request):
        allowed_usernames = set(getattr(settings, "MAINTENANCE_ALLOWED_USERNAMES", []))
        return (
            request.user.is_authenticated
            and request.user.username in allowed_usernames
        )

    def __call__(self, request):
        if not getattr(settings, "MAINTENANCE_MODE", False):
            return self.get_response(request)

        if self._is_admin_path(request):
            if self._is_exempt_path(request) or self._is_allowed_user(request):
                return self.get_response(request)
            return render(request, "maintenance.html", status=503)

        if self._is_exempt_path(request) or self._is_allowed_user(request):
            return self.get_response(request)

        return render(request, "maintenance.html", status=503)

