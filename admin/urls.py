"""admin URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse
from django.utils.translation import get_language
from jdash import views


def debug_lang(request):
    return HttpResponse(f"LANGUAGE: {get_language()}")

urlpatterns = [
    # Handles language switching via GET or POST at /i18n/setlang/
    path('i18n/', include('django.conf.urls.i18n')),
    path("debug/lang/", debug_lang),
    #path("api/studies-list/", views.studies_list, name="studies_list"),
]


urlpatterns += [
    path('keepalive/', lambda request: HttpResponse("pong"), name='keepalive'),
    path("session_check/", views.session_check, name="session_check"),
]

urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('jdash/', include('jdash.urls')),
    path('django_plotly_dash/', include('django_plotly_dash.urls')),

    path('', include('jdash.urls')),
    )

# Optional: serve static files in dev
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
