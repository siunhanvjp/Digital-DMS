from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from utils.exceptions.exceptions import NotFound, AuthenticationFailed


class UserManager(BaseUserManager):  # type: ignore
    def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        user_name: Optional[str] = None,
        is_active: Optional[bool] = False,
        is_expert_user: Optional[bool] = False,
    ) -> Any:
        if not email:
            raise ValueError("Users must have an email address")
        user: Any = User(email=self.normalize_email(email))
        user.first_name = first_name
        user.last_name = last_name
        user.username = user_name
        user.is_active = is_active
        user.is_expertuser = is_expert_user
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str) -> Any:
        user = self.create_user(email, password)
        user.is_superuser = True
        user.is_staff = True
        user.is_active = True
        user.is_expertuser = True
        user.save(using=self._db)
        return user


class User(AbstractUser):
    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS: list[str] = []
    uid = models.UUIDField(unique=True, default=uuid4, editable=False)
    email = models.EmailField(unique=True, verbose_name="email-address", max_length=255)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True, default=None)
    image = models.FileField(upload_to="images/", blank=True, null=True, default=None)

    # Required by django admin
    is_superuser = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    is_active = models.BooleanField(default=False)
    is_expertuser = models.BooleanField(default=False)

    last_login = models.DateTimeField(
        auto_now=False, auto_now_add=False, null=True, blank=True
    )
    date_joined = models.DateTimeField(auto_now=False, auto_now_add=True)

    @staticmethod
    def get_user_by_email(email: str):
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise NotFound(message_code="USER_NOT_FOUND")
        return user

    def check_active(self):
        if not self.is_active:
            raise AuthenticationFailed(message_code="USER_UNVERIFIED")
        return True
