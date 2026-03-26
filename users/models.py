from django.contrib.auth.models import AbstractUser
from django.db import models

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