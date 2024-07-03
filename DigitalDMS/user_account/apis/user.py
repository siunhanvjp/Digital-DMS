from typing import Optional

from ninja import File
from ninja.files import UploadedFile
from ninja_extra import api_controller, http_get, http_post, http_put

from ..models.user import User
from ..schema.payload import (
    UserChangePassword,
    UserLoginRequest,
    UserPasswordResetRequest,
    UserRegisterRequest,
    UserUpdateInfoRequest,
    UserPasswordRegisterRequest,
    EmailRequestResponse,
)
from ..schema.response import UserResponse
from router.authenticate import AuthBearer
from token_management.models.token import ResetToken
from token_management.services.create_login_token import LoginTokenService
from token_management.services.create_reset_token import ResetTokenService
from utils.exceptions import AuthenticationFailed, NotFound, ValidationError
from utils.mail import MailSenderService
from utils.services.Data_validate import BaseValidate


@api_controller(prefix_or_class="users", tags=["User"])
class UserController:
    @http_post("/register")
    def user_register(self, data: UserRegisterRequest):
        BaseValidate.validate_register(data=data.dict())
        if User.objects.filter(email=data.email).exists():
            raise ValidationError(message_code="EMAIL_HAS_BEEN_USED")
        User.objects.create_user(
            first_name=data.first_name,
            last_name=data.last_name,
            email=data.email,
            password=data.password,
            user_name=data.user_name,
            is_active=True,
            is_expert_user=data.is_expert_user,
        )
        return True

    @http_post("/login")
    def user_login(self, data: UserLoginRequest):
        user = User.get_user_by_email(email=data.email)
        if not user.check_password(data.password):
            raise AuthenticationFailed(message_code="INVALID_EMAIL_PASSWORD")
        user.check_active()
        return {"access_token": LoginTokenService().create_token(user=user)}

    @http_get("/get/me", response=UserResponse, auth=AuthBearer())
    def get_me(self, request):
        return request.user

    @http_put("/update/password", auth=AuthBearer())
    def change_password(self, request, data: UserChangePassword):
        BaseValidate.validate_password(password=data.new_password)
        user = request.user
        if data.current_password == data.new_password:
            raise ValidationError(message_code="SAME_PASSWORD")
        if not user.check_password(data.current_password):
            raise ValidationError(message_code="INVALID_PASSWORD")
        user.set_password(data.new_password)
        user.save()

    @http_post("/update/info", auth=AuthBearer())
    def update_info(self, request, data: UserUpdateInfoRequest):
        data = data.dict()
        BaseValidate.validate_info(data=data)
        user = request.user
        user.__dict__.update(
            {key: value for key, value in data.items() if value is not None}
        )
        user.save()

    @http_post("/logout", auth=AuthBearer())
    def logout(self, request):
        LoginTokenService.deactivate(user=request.user, token=request.auth)

    @http_post("/forgot-password")
    def forgot_password(self, data: EmailRequestResponse):
        BaseValidate.validate_email(email=data.email)
        MailSenderService(recipients=[data.email]).send_reset_password_email()
        return True

    @http_put("/reset-password")
    def password_reset_confirm(self, data: UserPasswordResetRequest):
        try:
            reset_token = ResetToken.objects.get(token=data.token)
        except ResetToken.DoesNotExist as e:
            raise NotFound(message_code="RESET_TOKEN_INVALID_OR_EXPIRED") from e
        if not ResetTokenService.check_valid(token=reset_token):
            raise ValidationError(message_code="RESET_TOKEN_INVALID_OR_EXPIRED")
        BaseValidate.validate_password(password=data.password)
        user = reset_token.user
        if user.check_password(data.password):
            raise AuthenticationFailed(message_code="SAME_PASSWORD")
        user.set_password(data.password)
        user.save()
        ResetTokenService.deactivate(user=user)

    @http_get("/live-search-email", auth=AuthBearer())
    def live_search_email(self, request):
        query = request.GET.get("query", "")
        users = User.objects.filter(email__icontains=query)
        search_results = [{"value": user.uid, "label": user.email} for user in users]
        return search_results
