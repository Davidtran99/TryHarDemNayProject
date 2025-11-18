from django.urls import path
from . import views

urlpatterns = [
    path("search/", views.search),
    path("chat/", views.chat),
    path("procedures/", views.procedures_list),
    path("procedures/<int:pk>/", views.procedures_detail),
    path("fines/", views.fines_list),
    path("fines/<int:pk>/", views.fines_detail),
    path("offices/", views.offices_list),
    path("offices/<int:pk>/", views.offices_detail),
    path("advisories/", views.advisories_list),
    path("advisories/<int:pk>/", views.advisories_detail),
]

