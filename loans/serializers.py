from rest_framework import serializers
from .models import Loan,LoanType,LoanApplication,LoanPayment,RepaymentSchedule,PublicLoanApplication,Client
from clients.serializers import ClientSerializer
from datetime import timedelta
from decimal import Decimal,ROUND_HALF_UP
class LoanTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanType
        fields = "__all__"

    def validate(self, data):
        if data["min_amount"] >= data["max_amount"]:
            raise serializers.ValidationError(
                "Minimum amount must be less than maximum amount"
            )

        if data["interest_rate"] < 0:
            raise serializers.ValidationError(
                "Interest rate cannot be negative"
            )

        if data["repayment_period_value"] <= 0:
            raise serializers.ValidationError(
                "Repayment period must be greater than 0"
            )

        return data

class LoanApplicationSerializer(serializers.ModelSerializer):
    loan_type_details = LoanTypeSerializer(source="loan_type", read_only=True)
    client_data=ClientSerializer(source='client',read_only=True)
    class Meta:
        model = LoanApplication
        fields = "__all__"
        read_only_fields = [
            "status",
            "reviewed_by",
            "is_signed",
            "signed_at",
            "client",
            "contract",
        ]

    def validate(self, data):
        loan_type = data.get("loan_type")
        amount = data.get("requested_amount")

        if loan_type:
            if amount < loan_type.min_amount or amount > loan_type.max_amount:
                raise serializers.ValidationError(
                    f"Amount must be between {loan_type.min_amount} and {loan_type.max_amount}"
                )

            if not loan_type.is_active:
                raise serializers.ValidationError("Loan type is not active")

        return data
class RepaymentScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepaymentSchedule
        fields = "__all__"


class LoanPaymentSerializer(serializers.ModelSerializer):
    loan_id = serializers.PrimaryKeyRelatedField(
        queryset=Loan.objects.all(),
        source="loan",
        write_only=True
    )

    loan = serializers.StringRelatedField(read_only=True)
    class Meta:
        model = LoanPayment
        fields = "__all__"
    def get_loan(self, obj):
        return {
            "id": obj.loan.id,
            "reference": str(obj.loan),
            "remaining_balance": obj.loan.remaining_balance,
        }


class LoanSerializer(serializers.ModelSerializer):
    client_names = serializers.CharField(source="client.names", read_only=True)
    loan_type_name = serializers.CharField(source="loan_type.name", read_only=True)

    schedules = RepaymentScheduleSerializer(many=True, read_only=True)
    payments = LoanPaymentSerializer(many=True, read_only=True)
    total_due = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = "__all__"
    def get_total_due(self, obj):
        return obj.total_repayment + obj.penalty_amount
class AdminCreateLoanSerializer(serializers.ModelSerializer):
    interest_rate = serializers.FloatField(write_only=True)
    duration_days = serializers.IntegerField(write_only=True)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2, write_only=True)
    class Meta:
        model = Loan
        fields = [
            "client",
            "loan_type",
            "loan_amount",
            "interest_rate",
            "duration_days",
            "disbursement_date",
        ]

    def create(self, validated_data):
        interest_rate = validated_data.pop("interest_rate")
        duration_days = validated_data.pop("duration_days")

        loan_amount = validated_data["loan_amount"]

        # ✅ Calculate interest
        interest_rate_decimal = Decimal(interest_rate) / Decimal("100")

        interest_amount = (
            loan_amount * interest_rate_decimal
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # ✅ Total repayment
        total_repayment = loan_amount + interest_amount

        # ✅ Dates
        disbursement_date = validated_data["disbursement_date"]
        repayment_due_date = disbursement_date + timedelta(days=duration_days)

        return Loan.objects.create(
            **validated_data,
            interest_amount=interest_amount,
            total_repayment=total_repayment,
            remaining_balance=total_repayment,
            repayment_due_date=repayment_due_date,
            status="active",
        )
    def validate(self, data):
        if data["loan_amount"] <= 0:
            raise serializers.ValidationError("Loan amount must be positive")

        if data["interest_rate"] <= 0:
            raise serializers.ValidationError("Interest rate must be greater than 0")

        return data
class PublicLoanApplicationSerializer(serializers.ModelSerializer):
    loan_type_details = serializers.SerializerMethodField()
    class Meta:
        model = PublicLoanApplication
        fields = "__all__"
        read_only_fields = ["status", "reviewed_by"]
    def get_loan_type_details(self, obj):
        if obj.loan_type:
            return LoanTypeSerializer(obj.loan_type).data
        return {}
    def validate(self, data):
        loan_type = data.get("loan_type")
        amount = data.get("requested_amount")
        email = data.get("email")
        # ✅ Validate loan amount range
        if loan_type and amount:
            if amount < loan_type.min_amount or amount > loan_type.max_amount:
                raise serializers.ValidationError(
                    f"Amount must be between {loan_type.min_amount} and {loan_type.max_amount}"
                )

        # ✅ Prevent duplicate applications
        national_id = data.get("national_id")
        if PublicLoanApplication.objects.filter(
            national_id=national_id, status="pending"
        ).exists():
            raise serializers.ValidationError(
                "You already have a pending application."
            )
          # replace with your actual client model

        if email and Client.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "A client with this email already exists. Please log in to proceed."
            )

        return data
class AdminLoanApplicationSerializer(serializers.ModelSerializer):

    class Meta:
        model = LoanApplication
        fields = "__all__"
        read_only_fields = ["signed_at", "created_at"]

    def validate_client(self, value):
        if not value:
            raise serializers.ValidationError("Client is required")
        return value

    def validate(self, data):
        client = data.get("client")
        loan_type = data.get("loan_type")
        amount = data.get("requested_amount")

        # 🚨 HARD SAFETY CHECK
        if not client:
            raise serializers.ValidationError({"client": "Client is required"})
        if not loan_type:
            raise serializers.ValidationError({"loan_type": "Loan type is required"})
        if not amount:
            raise serializers.ValidationError({"requested_amount": "Amount is required"})

        # convert safely
        try:
            amount = float(amount)
        except:
            raise serializers.ValidationError({"requested_amount": "Invalid amount"})

        # loan type rules
        if amount < loan_type.min_amount or amount > loan_type.max_amount:
            raise serializers.ValidationError(
                f"Amount must be between {loan_type.min_amount} and {loan_type.max_amount}"
            )

        # duplicate check
        if LoanApplication.objects.filter(
            client=client,
            loan_type=loan_type,
            status__in=["pending", "reviewed", "signed"]
        ).exists():
            raise serializers.ValidationError(
                "Client already has active application for this loan type"
            )

        return data