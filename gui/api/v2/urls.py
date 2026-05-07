from django.urls import path

from .views import health, user_settings

urlpatterns = [
    path("health/", health, name="api-v2-health"),
    path("user/settings/", user_settings, name="api-v2-user-settings"),
]
