from django.shortcuts import render
# from urllib3 import request

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import ChangePasswordSerializer 
from rest_framework import permissions
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from .serializers import LoginSerializer, ChangePasswordSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from django.views import View
from django.contrib.auth import get_user_model, authenticate
from django.db.models import Q
from .serializers import LoginSerializer
from rest_framework.viewsets import ModelViewSet
from .models import User
from .serializers import UserSerializer
from .permissions import IsAdminOrManagerOrReadOnlyReviewer
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from .models import PasswordResetRequest
import uuid
from django.utils import timezone
from datetime import timedelta
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils.decorators import method_decorator
User = get_user_model()
def checktemplates(request):
    return render(request,'emails/credentials.html')
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        print("REQUEST DATA:", request.data)

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        identifier = serializer.validated_data["identifier"].strip().lower()
        password = serializer.validated_data["password"]

        # 🔍 Find user by email OR username
        user = User.objects.filter(
            Q(email=identifier) | Q(username=identifier)
        ).first()

        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔐 Authenticate
        user = authenticate(username=user.username, password=password)

        if not user:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.is_active:
            return Response(
                {"error": "User is inactive"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 🎟 Generate tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "role": user.role,
            "must_change_password": user.must_change_password
        })

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"error": "Wrong password"}, status=400)

        user.set_password(serializer.validated_data["new_password"])
        user.must_change_password = False
        user.save()

        return Response({"message": "Password updated"})
#============================
# 🌐 USER ADMIN MANAGEMENT VIEW
#============================
class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by("-id")
    serializer_class = UserSerializer

    def get_permissions(self):
        user = self.request.user

        # 🔐 must be logged in
        if not user.is_authenticated:
            return [IsAuthenticated()]

        # 🔴 DELETE → admin only
        if self.action == "destroy":
            if user.role != "admin":
                self.permission_denied(self.request, message="Only admin can delete users")

        # 🟡 CREATE → admin + manager
        if self.action == "create":
            if user.role not in ["admin", "manager"]:
                self.permission_denied(self.request, message="Not allowed")

        # 🟡 UPDATE → admin + manager
        if self.action in ["update", "partial_update"]:
            if user.role not in ["admin", "manager"]:
                self.permission_denied(self.request, message="Not allowed")

        # 🟢 LIST / RETRIEVE → all staff roles
        if self.action in ["list", "retrieve"]:
            if user.role not in ["admin", "manager", "reviewer"]:
                self.permission_denied(self.request, message="Not allowed")

        return [IsAuthenticated()]


import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def contact_support(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            name = data.get("name")
            email = data.get("email")
            message = data.get("message")

            # ✅ Validation
            if not name or not email or not message:
                return JsonResponse({"success": False, "error": "All fields are required"})

            if "\n" in email or "\r" in email:
                return JsonResponse({"success": False, "error": "Invalid email"})

            subject = f"[Support] New message from {name}"

            context = {
                "name": name,
                "email": email,
                "message": message,
            }

            html_content = render_to_string("emails/contact_support.html", context)
            text_content = strip_tags(html_content)

            from_email = f"Kigali Microloans Support <{settings.EMAIL_HOST_USER}>"

            msg = EmailMultiAlternatives(
                subject,
                text_content,
                from_email,
                ["ngogainnocent1@gmail.com"],
                headers={"Reply-To": email}
            )

            msg.attach_alternative(html_content, "text/html")
            msg.send(fail_silently=False)

            # ✅ Auto reply
            auto_reply = EmailMultiAlternatives(
                "We received your message",
                f"Hi {name}, we received your request and will respond shortly.",
                from_email,
                [email],
            )
            auto_reply.send()

            logger.info(f"Support email sent from {email}")

            return JsonResponse({"success": True})

        except Exception as e:
            logger.error(str(e))
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"error": "Invalid request"}, status=400)

class PasswordResetView(APIView):

    # =========================
    # POST → Request reset
    # =========================
    def post(self, request):
        email = request.data.get("email")

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({"success": False, "error": "User not found"}, status=404)

        PasswordResetRequest.objects.create(user=user)

        return Response({
            "success": True,
            "message": "Request sent. Await admin approval."
        })


    # =========================
    # GET → Verify token
    # =========================
    def get(self, request, token=None):

        if not token:
            return Response({"error": "Token required"}, status=400)

        try:
            req = PasswordResetRequest.objects.get(token=token)

            if req.is_expired():
                req.status = "EXPIRED"
                req.save(update_fields=["status"])
                return Response({"valid": False, "error": "Token expired"})

            if req.status != "APPROVED":
                return Response({"valid": False, "error": "Invalid request"})

            return Response({"valid": True})

        except PasswordResetRequest.DoesNotExist:
            return Response({"valid": False, "error": "Invalid token"})


    # =========================
    # PUT → Reset password
    # =========================
    def put(self, request, token=None):

        if not token:
            return Response({"error": "Token required"}, status=400)

        password = request.data.get("password")

        try:
            req = PasswordResetRequest.objects.get(token=token)

            if req.is_expired():
                req.status = "EXPIRED"
                req.save(update_fields=["status"])
                return Response({"success": False, "error": "Token expired"})

            if req.status != "APPROVED":
                return Response({"success": False, "error": "Invalid request"})

            user = req.user
            user.password = make_password(password)
            user.save()

            req.status = "USED"
            req.save(update_fields=["status"])

            return Response({"success": True})

        except PasswordResetRequest.DoesNotExist:
            return Response({"success": False, "error": "Invalid token"})
class AdminPasswordResetView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):

        if request.user.role not in ["admin", "manager"]:
            return Response({"error": "Unauthorized"}, status=403)

        requests = PasswordResetRequest.objects.select_related("user").order_by("-created_at")

        data = [
            {
                "id": r.id,
                "email": r.user.email,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in requests
        ]

        return Response(data)
    def patch(self, request, request_id):

        user = request.user

        if user.role not in ["admin", "manager"]:
            return Response({"error": "Not allowed"}, status=403)

        try:
            req = PasswordResetRequest.objects.get(id=request_id)
        except PasswordResetRequest.DoesNotExist:
            return Response({"error": "Not found"}, status=404)

        if req.status != "PENDING":
            return Response({"error": "Already processed"}, status=400)

        token = str(uuid.uuid4())
        expiry = timezone.now() + timedelta(minutes=20)

        req.token = token
        req.status = "APPROVED"
        req.expires_at = expiry
        req.save()

        reset_link = f"{settings.FRONTEND_URL}/reset-password/{token}"

        send_mail(
            "Password Reset Approved",
            f"Reset your password (valid 20 min): {reset_link}",
            "info@tresinfra.com",
            [req.user.email],
        )
            
        return Response({"success": True})