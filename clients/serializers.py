from rest_framework import serializers
from .models import Client
from django.contrib.auth import get_user_model
import random, string
from users.utils import send_credentials_email
from loans.models import Loan
from django.db.models import Sum
User = get_user_model()
class UserMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "username", "role"]
class ClientSerializer(serializers.ModelSerializer):
    total_loans = serializers.IntegerField(read_only=True)
    total_amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    user_details = UserMiniSerializer(source="user", read_only=True)

    class Meta:
        model = Client
        fields = "__all__"
    def get_user_details(self, obj):
        if obj.user:
            return {
                "email": obj.user.email,
                "username": obj.user.username,
                "role": obj.user.role,
            }
        return {}
    


class CreateClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        exclude = ["user"]
    user_details = UserMiniSerializer(source="user", read_only=True)
    def generate_password(self):
        return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    def validate(self, data):
        id_document = data.get("id_document")
        job_contract = data.get("job_contract")
        bank_statement = data.get("bank_statement")

        if not id_document and not job_contract and not bank_statement:
            raise serializers.ValidationError(
                "You must upload at least one document (ID, Job Contract, or Bank Statement)."
            )

        return data

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def create(self, validated_data):
        password = self.generate_password()

        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=password,
            role="client",
            must_change_password=True
        )

        client = Client.objects.create(user=user, **validated_data)

        send_credentials_email(user.email, password)

        return client