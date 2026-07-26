from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    username = None
    phone = models.CharField(_('phone'), max_length=10, unique=True)
    full_name = models.CharField(_('full name'), max_length=150)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        return self.phone


class OTPPurpose(models.TextChoices):
    REGISTER = 'register'
    LOGIN = 'login'
    RESET_PASSWORD = 'reset_password'


class OTPCode(models.Model):
    phone = models.CharField(_('phone'), max_length=11)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_expired(self):
        return timezone.now > self.created_at + timedelta(minutes=2)
