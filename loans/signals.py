# loans/signals.py

from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils.timezone import now

from .models import Loan
from users.utils import send_email


@receiver(pre_save, sender=Loan)
def loan_status_change_handler(sender, instance: Loan, **kwargs):
    """
    Trigger email when loan status changes
    """

    # Skip new loans (no previous state)
    if not instance.pk:
        return

    try:
        old_loan = Loan.objects.get(pk=instance.pk)
    except Loan.DoesNotExist:
        return

    # Only act if status actually changed
    if old_loan.status == instance.status:
        return

    client = instance.client

    # 🔗 Common context
    context = {
        "client_name": getattr(client, "name", "Client"),
        "loan_id": instance.id,
        "status": instance.status,
        "balance": f"{instance.remaining_balance:,.0f}",
        "due_date": instance.repayment_due_date,
        "dashboard_url": "https://app.kigalimicroloans.com/dashboard",
        "payment_url": "https://app.kigalimicroloans.com/payments",
    }

    # 🎯 Route email based on status
    if instance.status in ["active", "in_payment"]:
        send_email(
            to_email=client.email,
            subject="Loan Activated",
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
            subject="Loan Default Notice",
            template_name="loans/loan_overdue.html",
            context=context,
        )

    else:
        # fallback generic update
        send_email(
            to_email=client.email,
            subject="Loan Status Update",
            template_name="emails/loan_status_update.html",
            context=context,
        )