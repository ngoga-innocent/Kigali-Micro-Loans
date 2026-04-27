from rest_framework import serializers
from django.contrib.auth import get_user_model
import random, string
from .models import PasswordResetRequest
from django.contrib.auth import authenticate
User = get_user_model()
from django.contrib.auth.password_validation import validate_password
from django.utils.crypto import get_random_string
from django.db import transaction
class CreateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "username", "role"]

    def generate_password(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value
    def validate_role(self, value):
        request = self.context.get("request")
        if request and request.user.role != "admin":
            raise serializers.ValidationError("Only admin can assign roles")
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists")
        return value
    def create(self, validated_data):
        password = self.generate_password()

        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=password,
            role=validated_data.get("role", "client"),
            must_change_password=True
        )

        from users.utils import send_credentials_email
        send_credentials_email(user.email, password)

        return user
class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()  # username OR email
    password = serializers.CharField()
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    def validate(self, data):
        validate_password(data["new_password"])
        return data

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "password"]

    # 🔐 secure generator
    def generate_password(self):
        return get_random_string(10)

    # ✅ basic validation
    def validate(self, data):
        if not data.get("username"):
            raise serializers.ValidationError({"username": "Username is required"})
        if not data.get("email"):
            raise serializers.ValidationError({"email": "Email is required"})
        return data

    # 🔒 prevent role abuse
    def validate_role(self, value):
        request = self.context.get("request")
        if request and request.user.role != "admin":
            raise serializers.ValidationError("Only admin can assign roles")
        return value

    def create(self, validated_data):
        password = validated_data.pop("password", None)

        # 👉 if no password provided → auto generate
        if not password:
            password = self.generate_password()

        validate_password(password)

        with transaction.atomic():
            user = User.objects.create_user(
                username=validated_data["username"],
                email=validated_data["email"],
                password=password,
                role=validated_data.get("role", "client"),
                must_change_password=True,
            )

            # optional: send email
            from users.utils import send_credentials_email
            send_credentials_email(user.email, password)

        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            validate_password(password)
            instance.set_password(password)

        instance.save()
        return instance
class PasswordResetRequestSerializer(serializers.ModelSerializer):
    email = serializers.CharField(source="user.email")

    class Meta:
        model = PasswordResetRequest
        fields = ["id", "email", "status", "created_at"]