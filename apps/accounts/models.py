from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.utils import timezone
from django.db.models import Q
from django.core.exceptions import ValidationError

from .managers import UserManager

from datetime import timedelta


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


class Province(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class City(models.Model):
    province = models.ForeignKey(
        Province,
        on_delete=models.CASCADE,
        related_name='cities',
    )
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses', verbose_name=_('user'))
    title = models.CharField(_('title'), max_length=50)
    recipient_name = models.CharField(_('recipient name'), max_length=100)
    phone = models.CharField(_('phone'), max_length=20)
    province = models.ForeignKey(Province, on_delete=models.PROTECT, verbose_name=_('province'))
    city = models.ForeignKey(City, on_delete=models.PROTECT, verbose_name=_('city'))
    postal_code = models.CharField(_('postal code'), max_length=20)
    address_line = models.TextField(_('address'))
    is_default = models.BooleanField(_('default'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    def __str__(self):
        return f'{self.title} - {self.recipient_name}'

    def clean(self):
        if self.city and self.province:
            if self.city.province_id != self.province_id:
                raise ValidationError(
                    _('City does not belong to selected province.')
                )

    class Meta:
        verbose_name = _('address')
        verbose_name_plural = _('addresses')

        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_default=True),
                name='unique_default_address_per_user',
            )
        ]