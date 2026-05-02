# users/urls.py

from django.urls import path
from .views import LoginView, ChangePasswordView,checktemplates,contact_support
from rest_framework.routers import DefaultRouter
from .views import UserViewSet,PasswordResetView,AdminPasswordResetView,generate_2fa,verify_2fa,disable_2fa
router = DefaultRouter()
router.register(r'users', UserViewSet)

urlpatterns = [
    path("login/", LoginView.as_view()),
    path('checktemps',checktemplates),
    path("2fa/generate/", generate_2fa),
    path("2fa/verify/", verify_2fa),
    path("2fa/disable/", disable_2fa),
    path("change-password/", ChangePasswordView.as_view()),
    path("password-reset/", PasswordResetView.as_view()),  # POST + admin GET
    path("password-reset/<str:token>/", PasswordResetView.as_view()),  # GET + PUT
    path("admin/password-reset/", AdminPasswordResetView.as_view()),
    path("admin/password-reset/<int:request_id>/<str:action>/", AdminPasswordResetView.as_view()),
    # path("admin/password-reset/<int:request_id>/reject/", AdminPasswordResetView.as_view()),
    # path("password-reset/approve/<int:request_id>/", PasswordResetView.as_view()),  # PATCH
    
    path("contact/", contact_support),
] + router.urls