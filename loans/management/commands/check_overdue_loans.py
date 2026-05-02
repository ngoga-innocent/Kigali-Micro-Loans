from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta,date

from loans.management.commands.reloan import process_reloan
from loans.models import Loan
from users.utils import send_email
from django.conf import settings
from .reloan import process_reloan
payment_url = f"{settings.FRONTEND_URL}/payments"

class Command(BaseCommand):
    help = "Loan reminders and overdue processing"

    def handle(self, *args, **kwargs):
        today = now().date()

        loans = Loan.objects.select_related("client").filter(
            status__in=["active", "in_payment","overdue"]
        )

        stats = {
            "5_days": 0,
            "1_day": 0,
            "due_today": 0,
            "overdue": 0,
        }

        for loan in loans:
            due_date = loan.repayment_due_date
            days_left = (due_date - today).days
            print("days remaining",days_left)
            context = {
                "client_name": loan.client.names,
                "loan_id": loan.id,
                "due_date": due_date,
                "balance": f"{loan.remaining_balance:,.0f}",
                "payment_url": payment_url,
            }

            # 🔔 5 DAYS BEFORE
            if days_left == 5 and not loan.reminder_5_days_sent:
                send_email(
                    to_email=loan.client.email,
                    subject="📅 Loan Payment Reminder (5 Days Left)",
                    template_name="loans/loan_reminder.html",
                    context=context,
                )
                loan.reminder_5_days_sent = True
                stats["5_days"] += 1

            # 🔔 1 DAY BEFORE
            elif days_left == 1 and not loan.reminder_1_day_sent:
                send_email(
                    to_email=loan.client.email,
                    subject="⏳ Loan Payment Due Tomorrow",
                    template_name="loans/loan_reminder.html",
                    context=context,
                )
                loan.reminder_1_day_sent = True
                stats["1_day"] += 1

            # 🔔 DUE AFTER GRACE PERIOD
            elif days_left < 0 and not loan.reminder_due_today_sent:
                if loan.is_eligible_for_reloan() and loan.status != "reloaned":
                    process_reloan(loan)
                    stats["overdue"] += 1
                    continue  # 🚨 skip penalty logic
                else:
                    send_email(
                        to_email=loan.client.email,
                        subject="📌 Loan Payment Due Today",
                        template_name="loans/loan_reminder.html",
                        context=context,
                    )
                    loan.reminder_due_today_sent = True
                    stats["due_today"] += 1

            # ⚠️ OVERDUE
            # ⚠️ OVERDUE
            elif days_left < 0:
                if loan.status != "overdue":
                    loan.status = "overdue"

                loan_type = loan.loan_type
                penalty_rate = loan_type.late_payment_penalty_percentage / 100
                grace_days = loan_type.grace_period_days
                today = date.today()

                penalty_applied = False

                # how many days overdue
                overdue_days = (today - due_date).days

                # Apply penalty DAILY after grace period
                if overdue_days > grace_days:
                    if loan.last_penalty_date != today:
                        penalty = loan.remaining_balance * penalty_rate

                        loan.penalty_amount += penalty
                        loan.remaining_balance += penalty
                        loan.last_penalty_date = today

                        penalty_applied = True

                # Send email once per day
                if (
                    loan.overdue_last_notified is None
                    or loan.overdue_last_notified != today
                ):
                    context["penalty"] = f"{loan.penalty_amount:,.0f}"
                    context["days_overdue"] = overdue_days

                    send_email(
                        to_email=loan.client.email,
                        subject="⚠️ Loan Overdue Notice",
                        template_name="loans/loan_overdue.html",
                        context=context,
                    )

                    loan.overdue_last_notified = today
                    stats["overdue"] += 1

        loan.save()
            

        self.stdout.write(self.style.SUCCESS(f"Done: {stats}"))