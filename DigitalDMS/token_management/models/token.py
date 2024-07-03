from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.db import models

from user_account.models.user import User


class LoginToken(models.Model):
    """Model for JWT token"""

    uid = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    user = models.ForeignKey(
        to=User,
        related_name="login_token_fk_user",
        on_delete=models.CASCADE,
        db_constraint=False,
        db_column="user_uid",
    )
    token = models.TextField(max_length=64, unique=True, null=False, blank=False)
    active = models.BooleanField(default=True, null=False, blank=False)
    created_at = models.DateTimeField(
        auto_now_add=True, auto_now=False, null=False, blank=False
    )
    deactivated_at = models.DateTimeField(null=True)


class ResetToken(models.Model):
    """Model representing token given when issuing reset"""

    uid = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    user = models.ForeignKey(
        to=User,
        related_name="reset_token_fk_user",
        on_delete=models.CASCADE,
        db_constraint=False,
        db_column="user_uid",
    )
    token = models.TextField(max_length=64, null=False, blank=False)
    active = models.BooleanField(default=True, null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    expire_at = models.DateTimeField(null=True, blank=False)

    def save(self, *args, **kwargs):
        self.expire_at = datetime.now() + timedelta(
            minutes=settings.RESET_PASSWORD_TOKEN_LIFETIME
        )
        super().save(*args, **kwargs)

    # class RegisterToken(models.Model):
    """Model representing token given when issuing reset"""

    # uid = models.UUIDField(default=uuid4, primary_key=True, editable=False)
    # user = models.ForeignKey(
    #     to=User,
    #     related_name="register_token_fk_user",
    #     on_delete=models.CASCADE,
    #     db_constraint=False,
    #     db_column="user_uid",
    # )
    # token = models.TextField(editable=False, max_length=64, null=False, blank=False)
    # active = models.BooleanField(editable=True, default=True, null=False, blank=False)
    # created_at = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    # expire_at = models.DateTimeField(null=True, blank=False)

    # def save(self, *args, **kwargs):
    #     self.expire_at = datetime.now() + timedelta(
    #         minutes=settings.REGISTER_TOKEN_LIFETIME
    #     )
    #     super().save(*args, **kwargs)
