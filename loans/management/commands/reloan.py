from django.conf import settings
from users.utils import send_email
from loans.models import Loan
from django.utils.timezone import now
from datetime import timedelta
def process_reloan(loan: Loan):
    if not loan.is_eligible_for_reloan():
        raise Exception("Loan is not eligible for reloan")

    if loan.remaining_balance <= 0:
        raise Exception("Loan already cleared")

    new_principal = loan.remaining_balance
    interest_rate = loan.loan_type.interest_rate / 100
    new_interest = new_principal * interest_rate

    from datetime import timedelta
    from django.utils.timezone import now

    new_due_date = now().date() + timedelta(
        days=loan.loan_type.repayment_period_value
    )

    new_loan = Loan.objects.create(
        client=loan.client,
        loan_type=loan.loan_type,
        loan_amount=new_principal,
        interest_amount=new_interest,
        remaining_balance=new_principal + new_interest,
        disbursement_date=now().date(),
        repayment_due_date=new_due_date,
        status="active",
        parent_loan=loan,
    )

    loan.status = "reloaned"
    loan.save()

    # ✅ Send email
    payment_url = f"{settings.FRONTEND_URL}/payments"

    send_email(
        to_email=loan.client.email,
        subject="🔁 Loan Restructured Successfully",
        template_name="loans/reloan.html",
        context={
            "name": loan.client.names,
            "old_loan_id": loan.id,
            "new_loan_id": new_loan.id,
            "new_amount": f"{new_principal:,.0f}",
            "due_date": new_due_date,
            "payment_url": payment_url,
        },
    )

    return new_loan