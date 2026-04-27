from email.mime import application
from django.shortcuts import render

# Create your views here.
from rest_framework import generics
from .models import Loan
from .serializers import LoanSerializer
from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from rest_framework.permissions import AllowAny
from .models import LoanType
from .serializers import LoanTypeSerializer,LoanApplicationSerializer,LoanPaymentSerializer,AdminCreateLoanSerializer,AdminLoanApplicationSerializer
from users.permissions import IsAdminOrManager,IsAdminOrManagerOrReadOnlyReviewer
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.utils.timezone import now
from .models import LoanApplication, Loan,RepaymentSchedule,LoanPayment
from clients.models import Client
from rest_framework.exceptions import NotFound,ValidationError
from .utils import calculate_due_date,get_installments
from decimal import Decimal,ROUND_HALF_UP
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from dateutil.relativedelta import relativedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.utils.dateparse import parse_date
from clients.serializers import CreateClientSerializer
from .models import Loan, LoanApplication, LoanPayment, RepaymentSchedule,PublicLoanApplication
from .serializers import LoanSerializer, LoanPaymentSerializer,PublicLoanApplicationSerializer
import traceback
from django.contrib.auth import get_user_model

from datetime import timedelta
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from rest_framework.decorators import action
import mimetypes


User=get_user_model()
class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        print(user)
        # =========================
        # 📅 FILTERS (SMART DEFAULT)
        # =========================
        start_date = parse_date(request.query_params.get("start_date")) \
            if request.query_params.get("start_date") else None

        end_date = parse_date(request.query_params.get("end_date")) \
            if request.query_params.get("end_date") else None

        status = request.query_params.get("status")

        today = timezone.now().date()

        # ✅ Default: last 30 days
        if not start_date and not end_date:
            end_date = today
            start_date = today - timedelta(days=30)

        # =========================
        # 🔐 BASE QUERYSETS
        # =========================
        if user.role in ["admin", "manager"]:
            loans = Loan.objects.all()
            applications = LoanApplication.objects.all()
            payments = LoanPayment.objects.all()
            schedules = RepaymentSchedule.objects.all()
        else:
            loans = Loan.objects.filter(client__user=user)
            applications = LoanApplication.objects.filter(client__user=user)
            payments = LoanPayment.objects.filter(loan__client__user=user)
            schedules = RepaymentSchedule.objects.filter(loan__client__user=user)

        # =========================
        # 📅 APPLY DATE FILTERS (FLEXIBLE)
        # =========================
        if start_date:
            loans = loans.filter(created_at__date__gte=start_date)
            applications = applications.filter(created_at__date__gte=start_date)
            payments = payments.filter(payment_date__gte=start_date)

        if end_date:
            loans = loans.filter(created_at__date__lte=end_date)
            applications = applications.filter(created_at__date__lte=end_date)
            payments = payments.filter(payment_date__lte=end_date)

        # =========================
        # 🔍 STATUS FILTER
        # =========================
        if status:
            loans = loans.filter(status=status)

        # =========================
        # 👑 ADMIN / MANAGER VIEW
        # =========================
        if user.role in ["admin", "manager"]:

            # ---------- KPIs ----------
            total_loans = loans.count()
            active_loans = loans.filter(status="active").count()
            overdue_loans = loans.filter(status="overdue").count()
            paid_loans = loans.filter(status="paid").count()

            total_disbursed = loans.aggregate(
                total=Sum("loan_amount")
            )["total"] or 0

            total_collected = payments.filter(status="approved").aggregate(
                total=Sum("amount_paid")
            )["total"] or 0

            pending_applications = applications.filter(status="pending").count()
            pending_payments = payments.filter(status="pending").count()
            overdue_schedules = schedules.filter(status="overdue").count()

            # ---------- CHARTS ----------
            monthly_loans = list(
                loans.annotate(month=TruncMonth("created_at"))
                .values("month")
                .annotate(
                    total=Sum("loan_amount"),
                    count=Count("id")
                )
                .order_by("month")
            )

            monthly_payments = list(
                payments.filter(status="approved")
                .annotate(month=TruncMonth("payment_date"))
                .values("month")
                .annotate(total=Sum("amount_paid"))
                .order_by("month")
            )

            loan_status_distribution = list(
                loans.values("status")
                .annotate(count=Count("id"))
            )

            application_status_distribution = list(
                applications.values("status")
                .annotate(count=Count("id"))
            )

            # ---------- TABLES ----------
            recent_loans = LoanSerializer(
                loans.order_by("-created_at")[:5],
                many=True
            ).data

            recent_payments = LoanPaymentSerializer(
                payments.order_by("-payment_date")[:5],
                many=True
            ).data

            return Response({
                "role": user.role,

                "meta": {
                    "start_date": start_date,
                    "end_date": end_date,
                },

                "kpis": {
                    "total_loans": total_loans,
                    "active_loans": active_loans,
                    "overdue_loans": overdue_loans,
                    "paid_loans": paid_loans,
                    "total_disbursed": total_disbursed,
                    "total_collected": total_collected,
                    "pending_applications": pending_applications,
                    "pending_payments": pending_payments,
                    "overdue_schedules": overdue_schedules,
                },

                "charts": {
                    "monthly_loans": monthly_loans,
                    "monthly_payments": monthly_payments,
                    "loan_status_distribution": loan_status_distribution,
                    "application_status_distribution": application_status_distribution,
                },

                "tables": {
                    "recent_loans": recent_loans,
                    "recent_payments": recent_payments,
                }
            })

        # =========================
        # 👤 CLIENT VIEW
        # =========================

        total_paid = payments.filter(status="approved").aggregate(
            total=Sum("amount_paid")
        )["total"] or 0

        active_loan = loans.filter(
            status__in=["active", "in_payment"]
        ).first()

        next_payment = schedules.filter(
            status="pending"
        ).order_by("due_date").first()

        payment_progress = {
            "paid": float(total_paid),
            "remaining": float(active_loan.remaining_balance)
            if active_loan else 0
        }

        monthly_payments = list(
            payments.filter(status="approved")
            .annotate(month=TruncMonth("payment_date"))
            .values("month")
            .annotate(total=Sum("amount_paid"))
            .order_by("month")
        )
        
        return Response({
            "role": "client",

            "meta": {
                "start_date": start_date,
                "end_date": end_date,
            },

            "kpis": {
                "total_loans": loans.count(),
                "active_loans": loans.filter(status="active").count(),
                "total_paid": total_paid,
            },

            "current_loan": LoanSerializer(active_loan).data
            if active_loan else None,

            "next_payment": {
                "amount": next_payment.total_amount if next_payment else None,
                "due_date": next_payment.due_date if next_payment else None,
            },

            "charts": {
                "payment_progress": payment_progress,
                "monthly_payments": monthly_payments,
            },

            "tables": {
                "recent_payments": LoanPaymentSerializer(
                    payments.order_by("-payment_date")[:5],
                    many=True
                ).data,

                "repayment_schedule": list(
                    schedules.order_by("due_date").values(
                        "installment_number",
                        "due_date",
                        "total_amount",
                        "paid_amount",
                        "status"
                    )
                )
            }
        })
class LoanTypeViewSet(ModelViewSet):
    queryset = LoanType.objects.all().order_by("-created_at")
    serializer_class = LoanTypeSerializer

    # 🔐 Dynamic permissions
    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsAdminOrManager()]
        return [AllowAny()]

    # 🔍 Filtering + Search
    def get_queryset(self):
        queryset = LoanType.objects.all().order_by("-created_at")

        is_active = self.request.query_params.get("is_active")
        min_amount = self.request.query_params.get("min_amount")
        max_amount = self.request.query_params.get("max_amount")
        search = self.request.query_params.get("search")

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        if min_amount:
            queryset = queryset.filter(min_amount__gte=min_amount)

        if max_amount:
            queryset = queryset.filter(max_amount__lte=max_amount)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset

    # 🧠 Custom create logic (you control business logic here)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            loan_type = serializer.save()

            return Response(
                {
                    "message": "Loan type created successfully",
                    "data": LoanTypeSerializer(loan_type).data
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 🧠 Custom update
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()

            return Response({
                "message": "Loan type updated successfully",
                "data": serializer.data
            })

        return Response(serializer.errors, status=400)

    # 🧠 Custom delete (safe delete option)
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Optional: prevent deletion if used in loans
        if instance.loan_set.exists():
            return Response(
                {"error": "Cannot delete loan type already in use"},
                status=400
            )

        instance.delete()

        return Response(
            {"message": "Loan type deleted successfully"},
            status=204
        )
class LoanListView(generics.ListAPIView):
    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        # ADMIN / MANAGER → see all loans
        if user.role in ["admin", "manager"]:
            return Loan.objects.select_related(
                "client", "loan_type", "application"
            ).prefetch_related("schedules", "payments").all()

        # CLIENT → see only their loans
        if user.role == "client":
            return Loan.objects.select_related(
                "client", "loan_type", "application"
            ).prefetch_related("schedules", "payments").filter(
                client__user=user
            )

        return Loan.objects.none()


class CreateLoanView(generics.CreateAPIView):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
class LoanViewSet(ModelViewSet):
    queryset = Loan.objects.all().order_by("-created_at")
    serializer_class = LoanSerializer

    @action(detail=False, methods=["post"], url_path="create-manual")
    def create_manual(self, request):
        serializer = AdminCreateLoanSerializer(data=request.data)

        if serializer.is_valid():
            loan = serializer.save()
            return Response(
                LoanSerializer(loan).data,
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
class AdminLoanApplicationViewSet(ModelViewSet):
    queryset = LoanApplication.objects.all().order_by("-created_at")
    serializer_class = AdminLoanApplicationSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    @action(detail=False, methods=["post"], url_path="create-manual")
    def create_manual(self, request):
        try:
            print("📥 RAW REQUEST DATA:", request.data)

            serializer = self.get_serializer(data=request.data)

            if not serializer.is_valid():
                print("❌ VALIDATION ERRORS:", serializer.errors)
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            print("✅ VALIDATED DATA:", serializer.validated_data)

            application = serializer.save()

            return Response(
                self.get_serializer(application).data,
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            print("🔥 ERROR:", str(e))
            traceback.print_exc()

            return Response(
                {"error": "Something went wrong", "details": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
class LoanApplicationViewSet(ModelViewSet):
    queryset = LoanApplication.objects.all().order_by("-created_at")
    serializer_class = LoanApplicationSerializer
    permission_classes = [IsAuthenticated]

    # 🔐 Role-based filtering
    def get_queryset(self):
        user = self.request.user
        
        if user.role in ['admin','manager']:
            return LoanApplication.objects.all().order_by("-created_at")
        try:
            client=Client.objects.get(user=user)
        except Client.DoesNotExist:
            raise NotFound("User is not registered as a client")

        return LoanApplication.objects.filter(client=client).order_by("-created_at")

    # ✅ CLIENT APPLIES
    def perform_create(self, serializer):
        user = self.request.user

        try:
            client = Client.objects.get(user=user)
        except Client.DoesNotExist:
            raise NotFound("Client does not exist")

        # ✅ Check for existing unpaid loans
        has_unpaid_loan = Loan.objects.filter(
            client=client
        ).exclude(status='paid').exists()

        if has_unpaid_loan:
            raise ValidationError("You already have an active/unpaid loan")

        serializer.save(
            client=client,
            status="pending"
        )

    # ✅ ADMIN REVIEW (APPROVE / REJECT)
    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrManager])
    def review(self, request, pk=None):
        application = self.get_object()

        decision = request.data.get("decision")
        comment = request.data.get("comment", "")

        if application.status != "pending":
            return Response(
                {"error": "Application already processed"},
                status=400
            )

        if decision == "reject":
            application.status = "rejected"
            application.comment = comment
            application.reviewed_by = request.user
            application.save()

            return Response({"message": "Application rejected"})

        if decision == "approve":
            application.status = "reviewed"
            application.reviewed_by = request.user
            application.comment = comment
            application.save()

            return Response({
                "message": "Application approved. Upload contract next."
            })

        return Response({"error": "Invalid decision"}, status=400)

    # ✅ ADMIN UPLOAD CONTRACT
    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrManager])
    def upload_contract(self, request, pk=None):
        application = self.get_object()

        if application.status != "reviewed":
            return Response(
                {"error": "Application must be reviewed first"},
                status=400
            )

        contract = request.FILES.get("contract")

        if not contract:
            return Response(
                {"error": "Contract file is required"},
                status=400
            )

        application.contract = contract
        application.save()

        return Response({"message": "Contract uploaded successfully"})

    # ✅ CLIENT SIGNS CONTRACT
    @action(detail=True, methods=["post"])
    def sign(self, request, pk=None):
        application = self.get_object()
        is_staff = request.user.role in ['admin', 'manager']
        is_owner = hasattr(request.user, "client") and application.client == request.user.client

        if not (is_staff or is_owner):
            return Response(
                {"error": "Not your application"},
                status=403
            )

        if not application.contract:
            return Response(
                {"error": "Contract not uploaded yet"},
                status=400
            )

        if application.is_signed:
            return Response(
                {"error": "Already signed"},
                status=400
            )
        file = request.FILES.get("file")
        print(request.FILES)
        print("FILES:", request.FILES)
        print("DATA:", request.data)
        print("CONTENT TYPE:", request.content_type)

        if not file:
            return Response({"error": "Signed file is required"}, status=400)
        try:
            application.signed_contract = file
            application.is_signed = True
            application.signed_at = now()
            application.status = "signed"
            application.save()
        except Exception as e:
            return Response({"message":f"failed to sign the contract {e}"})

        return Response({"message": "Contract signed successfully"})

    # ✅ FINAL APPROVAL → CREATE LOAN
    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrManager])
    def finalize(self, request, pk=None):
        application = self.get_object()

        if application.status != "signed":
            return Response({"error": "Client must sign first"}, status=400)

        if Loan.objects.filter(application=application).exists():
            return Response({"error": "Loan already created"}, status=400)

        loan_type = application.loan_type

        amount = Decimal(application.requested_amount)
        rate = Decimal(loan_type.interest_rate)
        period_value = loan_type.repayment_period_value
        period_unit = loan_type.repayment_period_unit
        frequency =  loan_type.repayment_frequency
        interest_type = loan_type.interest_type

        # ✅ Interest Calculation
        if interest_type == 'flat':
            interest = (amount * rate / Decimal("100"))
        else:
            interest = (amount * rate / Decimal("100"))

        disbursement_date = now().date()
        due_date = calculate_due_date(disbursement_date, period_value, period_unit)

        installments = get_installments(period_value,period_unit, frequency)

        principal_per_installment = (amount / installments).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        interest_per_installment = (interest / installments).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        current_date = disbursement_date
        total_repayment = amount + interest
        try:
            with transaction.atomic():

                loan = Loan.objects.create(
                    client=application.client,
                    loan_type=loan_type,
                    application=application,
                    loan_amount=amount,
                    remaining_balance=total_repayment,
                    total_repayment=total_repayment,
                    interest_amount=interest,
                    disbursement_date=disbursement_date,
                    repayment_due_date=due_date,
                    status="active",
                )

                for i in range(1, installments + 1):

                    if frequency == "daily":
                        current_date += timedelta(days=1)
                    elif frequency == "weekly":
                        current_date += timedelta(weeks=1)
                    elif frequency == "monthly":
                        current_date += relativedelta(months=1)

                    RepaymentSchedule.objects.create(
                        loan=loan,
                        installment_number=i,
                        due_date=current_date,
                        principal_amount=principal_per_installment,
                        interest_amount=interest_per_installment,
                        total_amount=principal_per_installment + interest_per_installment,
                    )

                application.status = "approved"
                application.save()

        except Exception as e:
            return Response(
                {"error": f"Failed to finalize loan: {str(e)}"},
                status=400
            )

        return Response({
            "message": "Loan created successfully",
            "loan_id": loan.id
        }, status=201)
class LoanPaymentViewSet(ModelViewSet):
    queryset = LoanPayment.objects.all().order_by("-payment_date")
    serializer_class = LoanPaymentSerializer
    permission_classes = [IsAuthenticated]

    # 🔐 ROLE-BASED ACCESS
    def get_queryset(self):
        user = self.request.user

        if user.role in ["admin", "manager"]:
            return LoanPayment.objects.select_related("loan").all().order_by("-payment_date")

        return LoanPayment.objects.select_related("loan").filter(
            loan__client__user=user
        ).order_by("-payment_date")

    # ✅ CLIENT CREATES PAYMENT (WITH PROOF)
    def perform_create(self, serializer):
        print(self.request.data)
        loan_id = self.request.data.get("loan_id")

        if not loan_id:
            raise ValidationError("Loan ID is required")

        try:
            loan = Loan.objects.get(id=loan_id)
        except Loan.DoesNotExist:
            raise NotFound("Loan not found")

        # 🔐 Client can only pay their own loan
        if self.request.user.role == "client":
            if loan.client.user != self.request.user:
                raise ValidationError("You cannot pay this loan")

        if loan.status == "paid":
            raise ValidationError("Loan already fully paid")

        amount = Decimal(self.request.data.get("amount_paid", 0))

        if amount <= 0:
            raise ValidationError("Payment amount must be greater than 0")

        serializer.save(
            loan=loan,
            status="pending"
        )

    # ✅ ADMIN REVIEW (APPROVE / REJECT)
    @action(detail=True, methods=["post"], permission_classes=[IsAdminOrManager])
    def review(self, request, pk=None):
        payment = self.get_object()
        action_type = request.data.get("action")

        if payment.status != "pending":
            return Response(
                {"error": "Payment already processed"},
                status=400
            )

        # ❌ REJECT
        if action_type == "reject":
            payment.status = "rejected"
            payment.reviewed_by = request.user
            payment.save()

            return Response({"message": "Payment rejected"})

        # ✅ APPROVE
        if action_type == "approve":
            loan = payment.loan

            if loan.remaining_balance <= 0:
                return Response({"error": "Loan already paid"}, status=400)

            if payment.amount_paid > loan.remaining_balance:
                return Response(
                    {"error": "Amount exceeds remaining loan balance"},
                    status=400
                )

            try:
                with transaction.atomic():

                    schedules = loan.schedules.filter(
                        status="pending"
                    ).order_by("due_date")

                    remaining_amount = Decimal(payment.amount_paid)

                    for schedule in schedules:

                        if remaining_amount <= 0:
                            break

                        schedule_remaining = schedule.total_amount - schedule.paid_amount

                        # FULL PAYMENT
                        if remaining_amount >= schedule_remaining:
                            schedule.paid_amount += schedule_remaining
                            schedule.status = "paid"
                            remaining_amount -= schedule_remaining

                        # PARTIAL PAYMENT
                        else:
                            schedule.paid_amount += remaining_amount
                            remaining_amount = Decimal("0.00")

                        schedule.save()

                    # 🔥 Update Loan Balance
                    loan.remaining_balance -= payment.amount_paid

                    # 🔥 Update Loan Status
                    if loan.remaining_balance <= 0:
                        loan.status = "paid"
                        loan.remaining_balance = Decimal("0.00")
                    else:
                        loan.status = "in_payment"

                    loan.save()

                    # ✅ Mark payment approved
                    payment.status = "approved"
                    payment.reviewed_by = request.user
                    payment.save()

            except Exception as e:
                return Response(
                    {"error": f"Payment processing failed: {str(e)}"},
                    status=400
                )

            return Response({"message": "Payment approved and applied successfully"})

        return Response({"error": "Invalid action"}, status=400)
class PublicLoanApplicationViewSet(ModelViewSet):
    queryset = PublicLoanApplication.objects.all().order_by("-created_at")
    serializer_class = PublicLoanApplicationSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        # 🚫 Public users should NOT see all applications
        if self.request.user.role in ['admin','manager','reviewer']:
            return super().get_queryset()
        return PublicLoanApplication.objects.none()
class AdminPublicLoanApplicationViewSet(ModelViewSet):
    queryset = PublicLoanApplication.objects.all().order_by("-created_at")
    serializer_class = PublicLoanApplicationSerializer
    permission_classes = [IsAdminOrManagerOrReadOnlyReviewer]

    # =========================
    # UPDATE (Admin / Manager only)
    # =========================
    def update(self, request, *args, **kwargs):
        if request.user.role not in ["admin", "manager"]:
            return Response({"error": "Not allowed"}, status=403)
        app = self.get_object()
        if app.status == "converted":
            return Response({"error": "Cannot edit converted application"}, status=400)    
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role not in ["admin", "manager"]:
            return Response({"error": "Not allowed"}, status=403)
        app = self.get_object()
        if app.status == "converted":
            return Response({"error": "Cannot edit converted application"}, status=400)
        return super().partial_update(request, *args, **kwargs)

    # =========================
    # REVIEW
    # =========================
    @action(detail=True, methods=["post"])
    def review(self, request, pk=None):
        if request.user.role not in ["admin", "manager"]:
            return Response({"error": "Not allowed"}, status=403)

        app = self.get_object()
        app.status = "reviewed"
        app.reviewed_by = request.user
        app.save()

        return Response({"message": "Application marked as reviewed"})

    # =========================
    # CONVERT → CLIENT + LOAN
    # =========================
    @action(detail=True, methods=["post"])
    def convert(self, request, pk=None):
        if request.user.role not in ["admin", "manager"]:
            return Response({"error": "Not allowed"}, status=403)

        app = self.get_object()

        if app.status == "converted":
            return Response({"error": "Already converted"}, status=400)

        link_existing = request.data.get("link_existing") == "true"

        try:
            with transaction.atomic():

                # =========================
                # 🔍 CHECK EXISTING USER
                # =========================
                existing_user = User.objects.filter(email=app.email).first()
                existing_client = None

                if existing_user:
                    existing_client = Client.objects.filter(user=existing_user).first()

                # =========================
                # 🚫 IF CLIENT EXISTS BUT NOT LINKING
                # =========================
                if existing_client and not link_existing:
                    return Response(
                        {"error": "Client already exists. Enable link existing to continue."},
                        status=400
                    )

                # =========================
                # ✅ USE EXISTING CLIENT
                # =========================
                if existing_client and link_existing:
                    client = existing_client

                    # 🔥 CHECK PENDING LOAN
                    has_pending_loan = LoanApplication.objects.filter(
                        client=client,
                        status="pending"
                    ).exists()

                    if has_pending_loan:
                        return Response(
                            {"error": "Client already has a pending loan"},
                            status=400
                        )

                # =========================
                # ✅ CREATE NEW CLIENT
                # =========================
                else:
                    client_data = {
                        "names": app.full_name,
                        "email": app.email,
                        "phone": app.phone,
                        "loan_type":app.loan_type,
                        "id_number": app.national_id,
                        "gender": app.gender,
                        "marital_status": app.marital_status,
                        "district": app.district,
                        "sector": app.sector,
                        "cell": app.cell,
                        "village": app.village,
                        "id_document": app.id_document,
                        "job_contract": app.job_contract,
                        "bank_statement": app.bank_statement,
                    }

                    serializer = CreateClientSerializer(data=client_data)
                    serializer.is_valid(raise_exception=True)
                    client = serializer.save()

                # =========================
                # ✅ CREATE LOAN APPLICATION
                # =========================
                loan_app = LoanApplication.objects.create(
                    client=client,
                    loan_type=app.loan_type,
                    requested_amount=app.requested_amount,
                    status="pending",
                )

                # =========================
                # ✅ UPDATE PUBLIC APPLICATION
                # =========================
                app.status = "converted"
                app.save()

            return Response({
                "message": "Converted successfully",
                "client_id": client.id,
                "loan_application_id": loan_app.id,
                "linked": bool(existing_client and link_existing)
            })

        except Exception as e:
            return Response({"detail": str(e)}, status=400)
    # =========================
    # REJECT
    # =========================
    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        if request.user.role not in ["admin", "manager"]:
            return Response({"error": "Not allowed"}, status=403)

        app = self.get_object()
        app.status = "rejected"
        app.reviewed_by = request.user
        app.comment = request.data.get("comment", "")
        app.save()

        return Response({"message": "Application rejected"})
    #===========================
    # DOWNLOAD ID DOCUMENT
    #===========================
    


    @action(detail=True, methods=["get"], url_path="view-file")
    def view_file(self, request, pk=None):
        app = self.get_object()
        file_type = request.query_params.get("type")

        file_map = {
            "id": app.id_document,
            "contract": app.job_contract,
            "bank": app.bank_statement,
        }

        file = file_map.get(file_type)

        if not file:
            return Response({"error": "File not found"}, status=404)

        file_path = file.path  # 🔥 IMPORTANT
        mime_type, _ = mimetypes.guess_type(file_path)

        with open(file_path, "rb") as f:
            response = HttpResponse(f.read(), content_type=mime_type or "application/pdf")

            # 🔥 THIS LINE FIXES YOUR ISSUE
            response["Content-Disposition"] = f'inline; filename="{file.name}"'

            return response