from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    BIDDER = "bidder", "Bidder"
    SELLER = "seller", "Seller"
    ADMIN = "admin", "Admin"


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.BIDDER,
    )

    @property
    def is_platform_admin(self) -> bool:
        return self.is_superuser or self.is_staff or self.role == UserRole.ADMIN

    @property
    def can_sell(self) -> bool:
        return self.is_platform_admin or self.role == UserRole.SELLER

