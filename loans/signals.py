# loans/signals.py

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings
from users.utils import get_staff_emails
from .models import Loan, PublicLoanApplication, LoanApplication,LoanPayment
from users.utils import send_email

dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
payment_url = f"{settings.FRONTEND_URL}/payments"

@receiver(pre_save, sender=Loan)
def loan_store_previous_state(sender, instance, **kwargs):
    """
    Store previous state BEFORE save for comparison
    """
    if instance.pk:
        instance._previous = Loan.objects.filter(pk=instance.pk).first()
    else:
        instance._previous = None


@receiver(post_save, sender=Loan)
def loan_post_save_handler(sender, instance, created, **kwargs):

    client = instance.client

    # =========================
    # 🆕 NEW LOAN (DISBURSED)
    # =========================
    if created:
        if client and client.email:
            send_email(
                to_email=client.email,
                subject="💰 Loan Disbursed Successfully",
                template_name="loans/loan_disbursed.html",
                context={
                    "client_name": getattr(client, "names", "Client"),
                    "loan_id": instance.id,
                    "amount": f"{instance.loan_amount:,.0f}",
                    "balance": f"{instance.remaining_balance:,.0f}",
                    "due_date": instance.repayment_due_date,
                    "dashboard_url": dashboard_url,
                    "role":"client",
                    "payment_url": payment_url,
                },
            )
            send_email(
                to_email=get_staff_emails(),
                subject="💰 Loan Disbursed Successfully",
                template_name="loans/loan_disbursed.html",
                context={
                    "client_name": getattr(client, "names", "Client"),
                    "loan_id": instance.id,
                    "amount": f"{instance.loan_amount:,.0f}",
                    "balance": f"{instance.remaining_balance:,.0f}",
                    "due_date": instance.repayment_due_date,
                    "dashboard_url": dashboard_url,
                    "role":"staff",
                    "payment_url": payment_url,
                },
            )
        return

    # =========================
    # 🔄 STATUS CHANGE HANDLER
    # =========================
    previous = getattr(instance, "_previous", None)

    if not previous or previous.status == instance.status:
        return

    context = {
        "client_name": getattr(client, "names", "Client"),
        "loan_id": instance.id,
        "amount": f"{instance.loan_amount:,.0f}",
        "balance": f"{instance.remaining_balance:,.0f}",
        "due_date": instance.repayment_due_date,
        "status": instance.status,
        "dashboard_url": dashboard_url,
        "payment_url": payment_url,
    }

    templates = {
        "active": ("📌 Loan Activated", "loans/loan_activated.html"),
        "in_payment": ("💳 Loan In Payment", "loans/loan_activated.html"),
        "overdue": ("⚠️ Loan Payment Overdue", "loans/loan_overdue.html"),
        "paid": ("✅ Loan Fully Repaid", "loans/loan_status_update.html"),
        "defaulted": ("🚨 Loan Default Notice", "loans/loan_overdue.html"),
        "reloaned": ("🔁 Loan Restructured", "loans/reloan.html"),
    }

    subject, template = templates.get(instance.status, (None, None))

    if subject and template and client and client.email:
        send_email(
            to_email=client.email,
            subject=subject,
            template_name=template,
            context=context,
        )
@receiver(pre_save, sender=PublicLoanApplication)
def public_application_store_previous(sender, instance, **kwargs):
    if instance.pk:
        instance._previous = PublicLoanApplication.objects.filter(pk=instance.pk).first()
    else:
        instance._previous = None
@receiver(post_save, sender=PublicLoanApplication)
def public_application_handler(sender, instance, created, **kwargs):

    # =========================
    # 🆕 NEW APPLICATION
    # =========================
    if created:
        if instance.email:
            send_email(
                to_email=instance.email,
                subject="📩 Loan Application Received",
                template_name="loans/application_received.html",
                context={
                    "name": instance.full_name,
                    "role":"client",
                    "amount": f"{instance.requested_amount:,.0f}",
                    "loan_type": instance.loan_type.name if instance.loan_type else "N/A",
                    "dashboard_url": dashboard_url,
                },
            )
            send_email(
                to_email=get_staff_emails(),
                subject="📩 Loan Application Received",
                template_name="loans/application_received.html",
                context={
                    "name": instance.full_name,
                    "role":"staff",
                    "amount": f"{instance.requested_amount:,.0f}",
                    "loan_type": instance.loan_type.name if instance.loan_type else "N/A",
                    "dashboard_url": dashboard_url,
                },
            )
        return

    # =========================
    # 🔄 STATUS CHANGE
    # =========================
    previous = getattr(instance, "_previous", None)

    if not previous or previous.status == instance.status:
        return

    templates = {
        "reviewed": ("Loan Application Reviewed", "loans/application_reviewed.html"),
        "converted": ("Loan Approved - Client Registered", "loans/application_converted.html"),
        "rejected": ("Loan Application Rejected", "loans/application_rejected.html"),
    }

    subject, template = templates.get(instance.status, (None, None))

    if subject and template and instance.email:
        send_email(
            to_email=instance.email,
            subject=subject,
            template_name=template,
            context={
                "name": instance.full_name,
                "amount": f"{instance.requested_amount:,.0f}",
                "loan_type": instance.loan_type.name if instance.loan_type else "N/A",
                "status": instance.status,
                "dashboard_url": dashboard_url,
            },
        )
        send_email(
            to_email=get_staff_emails(),
            subject=subject,
            template_name=template,
            context={
                "name": instance.full_name,
                "amount": f"{instance.requested_amount:,.0f}",
                "loan_type": instance.loan_type.name if instance.loan_type else "N/A",
                "status": instance.status,
                "dashboard_url": dashboard_url,
            },
        )
# =========================================
# STORE OLD STATUS
# =========================================
@receiver(pre_save, sender=LoanApplication)
def loan_application_pre_save(sender, instance, **kwargs):

    if not instance.pk:
        instance._old_status = None
        return

    try:
        old_instance = LoanApplication.objects.get(pk=instance.pk)
        instance._old_status = old_instance.status
    except LoanApplication.DoesNotExist:
        instance._old_status = None


# =========================================
# HANDLE EMAILS
# =========================================
@receiver(post_save, sender=LoanApplication)
def loan_application_post_save(sender, instance, created, **kwargs):

    client = instance.client

    context = {
        "name": client.names if client else "Client",
        "amount": f"{instance.requested_amount:,.0f}",
        "loan_type": instance.loan_type.name if instance.loan_type else "N/A",
        "status": instance.status,
        "dashboard_url": dashboard_url,
    }

    # =========================================
    # NEW APPLICATION
    # =========================================
    if created:

        print("NEW APPLICATION CREATED")

        # CLIENT EMAIL
        if client and client.email:
            send_email(
                to_email=client.email,
                subject="📩 Loan Application Received",
                template_name="loans/application_received.html",
                context={
                    **context,
                    "role": "client",
                },
            )

        # STAFF EMAIL
        

        send_email(
            to_email=get_staff_emails(),
            subject="📩 New Loan Application Submitted",
            template_name="loans/application_received.html",
            context={
                **context,
                "role": "staff",
            },
        )

        return

    # =========================================
    # STATUS CHANGE
    # =========================================
    old_status = getattr(instance, "_old_status", None)

    print("OLD STATUS:", old_status)
    print("NEW STATUS:", instance.status)

    # stop if no change
    if old_status == instance.status:
        return

    # =========================================
    # REVIEWED
    # =========================================
    if instance.status == "reviewed":

        print("SENDING REVIEWED EMAIL")

        if client and client.email:
            send_email(
                to_email=client.email,
                subject="📋 Loan Application Reviewed",
                template_name="loans/application_reviewed.html",
                context=context,
            )

    # =========================================
    # APPROVED
    # =========================================
    elif instance.status == "approved":

        print("SENDING APPROVED EMAIL")

        if client and client.email:
            send_email(
                to_email=client.email,
                subject="✅ Loan Application Approved",
                template_name="loans/application_approved.html",
                context=context,
            )

    # =========================================
    # REJECTED
    # =========================================
    elif instance.status == "rejected":

        print("SENDING REJECTED EMAIL")

        if client and client.email:
            send_email(
                to_email=client.email,
                subject="❌ Loan Application Rejected",
                template_name="loans/application_rejected.html",
                context=context,
            )
# =========================================
# 💳 LOAN PAYMENT SIGNALS
# =========================================

@receiver(pre_save, sender=LoanPayment)
def loan_payment_store_previous(sender, instance, **kwargs):

    if not instance.pk:
        instance._old_status = None
        return

    try:
        old_instance = LoanPayment.objects.get(pk=instance.pk)
        instance._old_status = old_instance.status
    except LoanPayment.DoesNotExist:
        instance._old_status = None


# =========================================
# STORE OLD STATUS BEFORE SAVE
# =========================================
@receiver(pre_save, sender=LoanPayment)
def loan_payment_pre_save(sender, instance, **kwargs):

    if not instance.pk:
        instance._old_status = None
        return

    try:
        old_instance = LoanPayment.objects.get(pk=instance.pk)
        instance._old_status = old_instance.status
    except LoanPayment.DoesNotExist:
        instance._old_status = None


# =========================================
# HANDLE EMAILS AFTER SAVE
# =========================================
@receiver(post_save, sender=LoanPayment)
def loan_payment_post_save(sender, instance, created, **kwargs):

    loan = instance.loan
    client = loan.client

    context = {
        "client_name": getattr(client, "names", "Client"),
        "loan_id": loan.id,
        "payment_id": instance.id,
        "amount_paid": f"{instance.amount_paid:,.0f}",
        "payment_date": instance.payment_date,
        "reference": instance.reference,
        "status": instance.status,
        "dashboard_url": dashboard_url,
        "payment_url": payment_url,
    }

    # =========================================
    # NEW PAYMENT CREATED
    # =========================================
    if created:

        print("NEW PAYMENT CREATED")

        # CLIENT EMAIL
        if client and client.email:
            send_email(
                to_email=client.email,
                subject="💳 Payment Submitted Successfully",
                template_name="loans/payment_submitted.html",
                context={
                    **context,
                    "role": "client",
                },
            )

        # STAFF EMAIL
        # from .utils import get_staff_emails

        send_email(
            to_email=get_staff_emails(),
            subject="💰 New Loan Payment Initiated",
            template_name="loans/payment_submitted.html",
            context={
                **context,
                "role": "staff",
            },
        )

        return

    # =========================================
    # STATUS CHANGE
    # =========================================
    old_status = getattr(instance, "_old_status", None)

    print("OLD STATUS:", old_status)
    print("NEW STATUS:", instance.status)

    # stop if no change
    if old_status == instance.status:
        return

    # =========================================
    # APPROVED
    # =========================================
    if instance.status == "approved":

        print("SENDING APPROVED EMAIL")

        if client and client.email:
            send_email(
                to_email=client.email,
                subject="✅ Payment Approved",
                template_name="loans/payment_approved.html",
                context=context,
            )

    # =========================================
    # REJECTED
    # =========================================
    elif instance.status == "rejected":

        print("SENDING REJECTED EMAIL")

        if client and client.email:
            send_email(
                to_email=client.email,
                subject="❌ Payment Rejected",
                template_name="loans/payment_rejected.html",
                context=context,
            )

    # =========================================
    # CANCELLED
    # =========================================
    elif instance.status == "cancelled":

        print("SENDING CANCELLED EMAIL")
        print(client.email)
        if client and client.email:
            send_email(
                to_email=client.email,
                subject="⚠️ Payment Cancelled",
                template_name="loans/payment_cancelled.html",
                context=context,
            )