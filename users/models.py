from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('manager', 'Credit Manager'),
        ('reviewer', 'Reviewer'),
        ('client', 'Client'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client')
    must_change_password = models.BooleanField(default=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)  


class PasswordResetRequest(models.Model):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("USED", "Used"),
        ("EXPIRED", "Expired"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="PENDING")

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        return self.expires_at and timezone.now() > self.expires_at