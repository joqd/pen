from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .product_model import Product

User = get_user_model()


class ReviewStatus(models.TextChoices):
    PENDING = 'pending', _('pending')
    APPROVED = 'approved', _('approved')
    REJECTED = 'rejected', _('rejected')


class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews', verbose_name=_('user'))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews', verbose_name=_('product'))
    rating = models.PositiveSmallIntegerField(_('rating'), validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(_('comment'))
    status = models.CharField(_('status'), max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('review')
        verbose_name_plural = _('reviews')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_user_product_review'),
        ]
        indexes = [
            models.Index(fields=['product', 'status']),
            models.Index(fields=['status', 'created_at']),
        ]

    def __str__(self):
        return f'{self.user} -> {self.product} ({self.rating})'
