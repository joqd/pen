from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    username = None
    phone = models.CharField(_('phone'), max_length=14, unique=True)  # +98 905 123 1234
    full_name = models.CharField(_('full name'), max_length=150)
    avatar = models.ImageField(_('avatar'), upload_to='avatars/', blank=True, null=True)

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = []
    objects = UserManager()

    def __str__(self):
        if self.full_name:
            return f'{self.full_name} ({self.phone})'
        return self.phone


class OTPPurpose(models.TextChoices):
    REGISTER = 'register'
    LOGIN = 'login'
    RESET_PASSWORD = 'reset_password'


class OTPCode(models.Model):
    phone = models.CharField(_('phone'), max_length=14)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def is_expired(self):
        return timezone.now > self.created_at + timedelta(minutes=2)
