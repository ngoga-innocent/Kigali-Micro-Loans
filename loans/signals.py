# loans/signals.py

from django.db.models.signals import pre_save,post_save
from django.dispatch import receiver
from django.utils.timezone import now

from .models import Loan,PublicLoanApplication
from users.utils import send_email
from django.conf import settings

dashboard_url = f"{settings.FRONTEND_URL}/dashboard"


@receiver(post_save, sender=Loan)
def loan_status_change_handler(sender, instance: Loan, **kwargs):
    """
    Trigger email when:
    1️⃣ Loan is created (disbursed)
    2️⃣ Loan status changes
    """

    dashboard_url = f"{settings.FRONTEND_URL}/dashboard"
    payment_url = f"{settings.FRONTEND_URL}/payments"

    client = instance.client

    # =========================
    # 🆕 NEW LOAN CREATED
    # =========================
    if instance._state.adding:
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
                "payment_url": payment_url,
            },
        )
        return  # 🚨 stop here for new loan

    # =========================
    # 🔄 EXISTING LOAN UPDATE
    # =========================
    try:
        old_loan = Loan.objects.get(pk=instance.pk)
    except Loan.DoesNotExist:
        return

    # Only act if status actually changed
    if old_loan.status == instance.status:
        return

    # 🔗 Common context
    context = {
        "client_name": getattr(client, "names", "Client"),
        "loan_id": instance.id,
        "status": instance.status,
        "balance": f"{instance.remaining_balance:,.0f}",
        "due_date": instance.repayment_due_date,
        "dashboard_url": dashboard_url,
        "payment_url": payment_url,
    }

    # =========================
    # 🎯 STATUS ROUTING
    # =========================
    if instance.status in ["active", "in_payment"]:
        send_email(
            to_email=client.email,
            subject="📌 Loan Activated",
            template_name="loans/loan_disbursed.html",
            context=context,
        )

    elif instance.status == "overdue":
        send_email(
            to_email=client.email,
            subject="⚠️ Loan Payment Overdue",
            template_name="loans/loan_overdue.html",
            context=context,
        )

    elif instance.status == "paid":
        send_email(
            to_email=client.email,
            subject="✅ Loan Fully Repaid",
            template_name="loans/loan_status_update.html",
            context={
                **context,
                "status": "paid",
            },
        )

    elif instance.status == "defaulted":
        send_email(
            to_email=client.email,
            subject="🚨 Loan Default Notice",
            template_name="loans/loan_overdue.html",
            context=context,
        )

    elif instance.status == "reloaned":
        send_email(
            to_email=client.email,
            subject="🔁 Loan Restructured",
            template_name="loans/reloan.html",
            context={
                **context,
                "old_loan_id": instance.id,
            },
        )

    else:
        send_email(
            to_email=client.email,
            subject="Loan Status Update",
            template_name="emails/loan_status_update.html",
            context=context,
        )
@receiver(pre_save, sender=PublicLoanApplication)
def loan_pre_save_handler(sender, instance: PublicLoanApplication, **kwargs):
    """
    Trigger emails when:
      1️⃣ A new loan application is created
      2️⃣ Status of an existing application changes
    """

    # 1️⃣ New application
    if instance._state.adding:
        send_email(
            to_email=instance.email,
            subject="Loan Application Received",
            template_name="loans/application_received.html",
            context={
                "name": instance.full_name,
                "amount": f"{instance.requested_amount:,.0f}",
                "loan_type": instance.loan_type.name if instance.loan_type else "N/A",
                "dashboard_url": dashboard_url,
            },
        )
        return  # no need to check status for new instance

    # 2️⃣ Existing application: check if status changed
    try:
        previous = PublicLoanApplication.objects.get(pk=instance.pk)
    except PublicLoanApplication.DoesNotExist:
        previous = None

    if previous and previous.status != instance.status:
        # Customize subject and template based on new status
        status_templates = {
            "reviewed": ("Loan Application Reviewed", "loans/application_reviewed.html"),
            "converted": ("Loan Approved - Client Registered", "loans/application_converted.html"),
            "rejected": ("Loan Application Rejected", "loans/application_rejected.html"),
        }

        subject, template = status_templates.get(instance.status, (None, None))
        if subject and template:
            send_email(
                to_email=instance.email,
                subject=subject,
                template_name=template,
                context={
                    "name": instance.full_name,
                    "amount": f"{instance.requested_amount:,.0f}",
                    "loan_type": instance.loan_type.name if instance.loan_type else "N/A",
                    "status": instance.status.capitalize(),
                    "dashboard_url": dashboard_url,
                },
            )