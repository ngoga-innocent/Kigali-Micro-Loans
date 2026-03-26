from django.contrib import admin
from .models import Loan,LoanApplication,LoanPayment,LoanType,RepaymentSchedule
# Register your models here.
admin.site.register(Loan)
admin.site.register(LoanApplication)
admin.site.register(LoanPayment)
admin.site.register(RepaymentSchedule)