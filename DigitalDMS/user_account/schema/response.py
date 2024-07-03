from ninja import ModelSchema

from ..models import User


class UserResponse(ModelSchema):
    class Config:
        model = User
        model_fields = (
            "first_name",
            "last_name",
            "email",
            "date_joined",
            "is_active",
            "is_expertuser",
            "username",
            "last_login",
        )
