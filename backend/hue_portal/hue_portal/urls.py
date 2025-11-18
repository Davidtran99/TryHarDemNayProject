from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("hue_portal.core.urls")),
    path("api/chatbot/", include("hue_portal.chatbot.urls")),
]

