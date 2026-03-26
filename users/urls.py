# users/urls.py

from django.urls import path
from .views import LoginView, ChangePasswordView,checktemplates

urlpatterns = [
    path("login/", LoginView.as_view()),
    path('checktemps',checktemplates),
    path("change-password/", ChangePasswordView.as_view()),
]