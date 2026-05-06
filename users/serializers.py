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
            phone_number=validated_data["phone_number"],
            full_name=validated_data["full_name"],
            id_card=validated_data['id_card'],
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
        fields = ["id", "username", "email", "role","is_2fa_enabled", "password","phone_number","id_card","full_name"]

    # 🔐 secure generator
    def generate_password(self):
        return get_random_string(10)

    # ✅ basic validation
    def validate(self, data):
        if self.instance and self.partial:
            return data

        if not data.get("username"):
            raise serializers.ValidationError({"username": "Username is required"})
        if not data.get("email"):
            raise serializers.ValidationError({"email": "Email is required"})

        return data

    # 🔒 prevent role abuse
    def validate_role(self, value):
        request = self.context.get("request")

        if not request:
            return value

        user = request.user

        # 🟢 Admin → can assign any role
        if user.role == "admin":
            return value

        # 🟡 Manager → limited roles
        if user.role == "manager":
            if value not in ["client", "reviewer"]:
                raise serializers.ValidationError(
                    "Managers can only assign client or reviewer roles"
                )
            return value

        # 🔴 Others → no role assignment allowed
        raise serializers.ValidationError(
            "You are not allowed to assign roles"
        )

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
                phone_number=validated_data["phone_number"],
                full_name=validated_data["full_name"],
                id_card=validated_data['id_card'],
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
class MeSerializer(serializers.ModelSerializer):
    is_profile_complete = serializers.SerializerMethodField()
    missing_fields = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "phone_number",
            "full_name",
            "id_card",
            "role",
            "is_2fa_enabled",
            "must_change_password",
            "is_profile_complete",
            "missing_fields",
        ]
        read_only_fields = [
            "role",  # 🔒 prevent privilege escalation
            "is_2fa_enabled",
            "must_change_password",
        ]

    def get_missing_fields(self, obj):
        missing = []
        if not obj.phone_number:
            missing.append("Phone Number")
        if not obj.full_name:
            missing.append("Full Names")
        if not obj.id_card:
            missing.append("Id Card")
        return missing

    def get_is_profile_complete(self, obj):
        return len(self.get_missing_fields(obj)) == 0