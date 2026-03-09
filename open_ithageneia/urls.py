"""
URL configuration for sonic_inertia project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    # TODO made by alkis remove
    path("language-test-example/", views.language_test_example, name="language-test-example"),
    re_path(r"^full-test-example/.*$", views.full_test_example, name="full-test-example"),
    path("quiz/", include("quiz.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
