# loans/signals.py

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.conf import settings

from .models import Loan, PublicLoanApplication, LoanApplication
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
#=========================================
# 🏦 LOAN APPLICATION SIGNALS
#=========================================
@receiver(pre_save, sender=LoanApplication)
def loan_application_store_previous(sender, instance, **kwargs):
    if instance.pk:
        instance._previous = LoanApplication.objects.filter(pk=instance.pk).first()
    else:
        instance._previous = None
@receiver(post_save, sender=LoanApplication)
def loan_application_handler(sender, instance, created, **kwargs):

    client = instance.client

    # =========================
    # 🆕 NEW APPLICATION
    # =========================
    if created:
        if client and client.email:
            send_email(
                to_email=client.email,
                subject="📩 Loan Application Received",
                template_name="loans/application_received.html",
                context={
                    "name": client.names,
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
        "approved": ("Loan Approved", "loans/application_approved.html"),
        "rejected": ("Loan Application Rejected", "loans/application_rejected.html"),
    }

    subject, template = templates.get(instance.status, (None, None))

    if subject and template and client and client.email:
        send_email(
            to_email=client.email,
            subject=subject,
            template_name=template,
            context={
                "name": client.names,
                "amount": f"{instance.requested_amount:,.0f}",
                "loan_type": instance.loan_type.name if instance.loan_type else "N/A",
                "status": instance.status,
                "dashboard_url": dashboard_url,
            },
        )