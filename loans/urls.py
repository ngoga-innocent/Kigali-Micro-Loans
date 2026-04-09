from django.urls import path
from .views import LoanListView, CreateLoanView
from rest_framework.routers import DefaultRouter
from .views import LoanTypeViewSet,LoanApplicationViewSet,LoanPaymentViewSet,DashboardView,PublicLoanApplicationViewSet,AdminPublicLoanApplicationViewSet,LoanViewSet

router = DefaultRouter()
router.register(r'loan-types', LoanTypeViewSet, basename='loan-type')
router.register(r'loan-applications', LoanApplicationViewSet, basename='loan-applications')
router.register(r'loan-payments', LoanPaymentViewSet, basename='loan-payments')
router.register(r"public-applications", PublicLoanApplicationViewSet, basename="public")
router.register(r"admin/public-applications", AdminPublicLoanApplicationViewSet, basename="admin-public")
router.register(r"loans", LoanViewSet, basename="loan")
urlpatterns = router.urls
urlpatterns += [
    path("list", LoanListView.as_view()),
    path("create/", CreateLoanView.as_view()),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
]