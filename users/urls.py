# users/urls.py

from django.urls import path
from .views import LoginView, ChangePasswordView,checktemplates
from rest_framework.routers import DefaultRouter
from .views import UserViewSet
router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path("login/", LoginView.as_view()),
    path('checktemps',checktemplates),
    path("change-password/", ChangePasswordView.as_view()),
] + router.urls