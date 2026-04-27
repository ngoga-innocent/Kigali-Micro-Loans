# users/urls.py

from django.urls import path
from .views import LoginView, ChangePasswordView,checktemplates,contact_support
from rest_framework.routers import DefaultRouter
from .views import UserViewSet,PasswordResetView,AdminPasswordResetView
router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path("login/", LoginView.as_view()),
    path('checktemps',checktemplates),
    path("change-password/", ChangePasswordView.as_view()),
    path("password-reset/", PasswordResetView.as_view()),  # POST + admin GET
    path("password-reset/<str:token>/", PasswordResetView.as_view()),  # GET + PUT
    path("admin/password-reset/", AdminPasswordResetView.as_view()),
    path("admin/password-reset/<int:request_id>/approve/", AdminPasswordResetView.as_view()),
    # path("password-reset/approve/<int:request_id>/", PasswordResetView.as_view()),  # PATCH
    
    path("contact/", contact_support),
] + router.urls