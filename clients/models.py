from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    id_number = models.CharField(max_length=50)
    names = models.CharField(max_length=255)
    gender = models.CharField(max_length=10)

    district = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    cell = models.CharField(max_length=100)
    village = models.CharField(max_length=100)

    marital_status = models.CharField(max_length=20)

    email = models.EmailField()
    phone = models.CharField(max_length=20)

    id_document = models.FileField(upload_to="documents/id/",null=True,blank=True)
    job_contract = models.FileField(upload_to="documents/job/",null=True,blank=True)
    bank_statement = models.FileField(upload_to="documents/bank/",null=True,blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.names