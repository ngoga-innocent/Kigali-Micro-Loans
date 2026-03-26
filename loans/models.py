from django.db import models
from clients.models import Client
from django.contrib.auth import get_user_model
User = get_user_model()
class LoanType(models.Model):
    PERIOD_UNIT = (
        ("days", "Days"),
        ("weeks", "Weeks"),
        ("months", "Months"),
    )

    REPAYMENT_FREQUENCY = (
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
    )

    INTEREST_TYPE = (
        ("flat", "Flat Rate"),
        ("reducing", "Reducing Balance"),
    )

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    min_amount = models.DecimalField(max_digits=12, decimal_places=2)
    max_amount = models.DecimalField(max_digits=12, decimal_places=2)

    interest_rate = models.DecimalField(max_digits=5, decimal_places=2)
    interest_type = models.CharField(max_length=20, choices=INTEREST_TYPE)

    repayment_period_value = models.IntegerField()
    repayment_period_unit = models.CharField(max_length=10, choices=PERIOD_UNIT)

    repayment_frequency = models.CharField(max_length=10, choices=REPAYMENT_FREQUENCY)

    processing_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    late_payment_penalty_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    grace_period_days = models.IntegerField(default=0)

    requires_collateral = models.BooleanField(default=False)
    collateral_description = models.TextField(blank=True)
    currency = models.CharField(max_length=10, default="RWF")
    max_concurrent_loans = models.IntegerField(default=1)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
class LoanApplication(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("reviewed", "Reviewed"),  # admin approved but waiting contract/sign
        ("signed", "Signed"),      # client signed contract
        ("approved", "Approved"),  # final approval → loan created
        ("rejected", "Rejected"),
    )

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    loan_type = models.ForeignKey(LoanType, on_delete=models.CASCADE)

    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    comment = models.TextField(blank=True)

    # 🔥 NEW FIELDS
    contract = models.FileField(upload_to="contracts/", null=True, blank=True)
    signed_contract=models.FileField(upload_to="signed_contract/",null=True,blank=True)
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
class Loan(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('in_payment', 'In Payment Period'),
        ('overdue', 'Overdue'),
        ('defaulted', 'Defaulted'),
        ('paid', 'Paid Off'),
    )

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    loan_type = models.ForeignKey(LoanType, on_delete=models.SET_NULL, null=True)
    application = models.OneToOneField(LoanApplication, on_delete=models.SET_NULL, null=True)

    loan_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=12, decimal_places=2)

    total_repayment = models.DecimalField(max_digits=12, decimal_places=2)

    disbursement_date = models.DateField()
    repayment_due_date = models.DateField()

    remaining_balance = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    contract = models.FileField(upload_to="contracts/", null=True, blank=True)
    # models.py

    reminder_5_days_sent = models.BooleanField(default=False)
    reminder_1_day_sent = models.BooleanField(default=False)
    reminder_due_today_sent = models.BooleanField(default=False)

    penalty_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    penalty_applied = models.BooleanField(default=False)
    last_penalty_date = models.DateField(null=True, blank=True)  # prevents duplicate daily penalties
    overdue_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.total_repayment = self.loan_amount + self.interest_amount

        

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Loan #{self.id} - {self.client}"
class RepaymentSchedule(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("overdue", "Overdue"),
    )

    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="schedules")

    installment_number = models.IntegerField()
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    due_date = models.DateField()

    principal_amount = models.DecimalField(max_digits=12, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=12, decimal_places=2)

    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    def __str__(self):
        return f"Loan {self.loan.id} - Installment {self.installment_number}"
class LoanPayment(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name="payments")
    schedule = models.ForeignKey(
        RepaymentSchedule, on_delete=models.SET_NULL, null=True, blank=True
    )

    amount_paid = models.DecimalField(max_digits=12, decimal_places=2)
    payment_proof = models.FileField(upload_to="payment_proofs/",null=True,blank=True)
    payment_date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    reference = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.loan} - {self.amount_paid}"