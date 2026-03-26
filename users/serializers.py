from rest_framework import serializers
from django.contrib.auth import get_user_model
import random, string
from django.contrib.auth import authenticate
User = get_user_model()
from django.contrib.auth.password_validation import validate_password


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