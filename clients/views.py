from rest_framework import generics
from .models import Client
from .serializers import ClientSerializer, CreateClientSerializer
from rest_framework import generics
from .models import Client
from .serializers import ClientSerializer, CreateClientSerializer
from users.permissions import IsAdminOrManager
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum,Value,DecimalField
from django.db.models.functions import Coalesce

# users/permissions.py


class ClientListCreateView(generics.ListCreateAPIView):
    # queryset = Client.objects.all()
    permission_classes = [IsAuthenticated, IsAdminOrManager]
    
    def get_queryset(self):
        return Client.objects.select_related("user").annotate(
            total_loans=Count("loan"),
            total_amount=Coalesce(
                Sum("loan__loan_amount"),
                Value(0),
                output_field=DecimalField(max_digits=12, decimal_places=2)
            )
        )
    def get_serializer_class(self):
        if self.request.method == "POST":
            return CreateClientSerializer
        return ClientSerializer


class ClientDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated, IsAdminOrManager]

