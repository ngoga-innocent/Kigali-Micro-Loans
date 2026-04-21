from django.shortcuts import render

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
from django.contrib.auth import get_user_model, authenticate
from django.db.models import Q
from .serializers import LoginSerializer
from rest_framework.viewsets import ModelViewSet
from .models import User
from .serializers import UserSerializer
from .permissions import IsAdminOrManagerOrReadOnlyReviewer
from rest_framework.permissions import IsAuthenticated
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