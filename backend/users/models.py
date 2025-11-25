from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

class UserRole(models.TextChoices):
    CLIENT = 'CLIENT', 'Клиент'
    OPERATOR = 'OPERATOR', 'Оператор'
    ADMIN = 'ADMIN', 'Администратор'

class User(AbstractUser):
    role = models.CharField(
        _('роль'),
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CLIENT
    )
    company_name = models.CharField(_('название компании'), max_length=255, blank=True)
    balance_minutes = models.IntegerField(_('баланс минут'), default=0)
    is_active_operator = models.BooleanField(_('активный оператор'), default=True)
    performance_metric = models.FloatField(_('показатель производительности'), default=0.0)

    def __str__(self):
        return self.email or self.username or f"User {self.pk}"

    @property
    def is_client(self):
        return self.role == UserRole.CLIENT

    @property
    def is_operator(self):
        return self.role == UserRole.OPERATOR

    @property
    def is_admin(self):
        return self.role == UserRole.ADMIN

    def has_sufficient_balance(self, video_duration):
        return self.balance_minutes >= video_duration

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower()
            # Keep username in sync with email
            self.username = self.email
        super().save(*args, **kwargs)

    class Meta:
        ordering = ('-date_joined',)
        constraints = [
            models.UniqueConstraint(fields=['email'], name='unique_user_email')
        ]
