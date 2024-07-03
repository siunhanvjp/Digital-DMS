from datetime import datetime

from django.conf import settings

from ninja.security import HttpBearer

import jwt
from token_management.models.token import LoginToken
from user_account.models.user import User
from utils.exceptions import AuthenticationFailed, NotFound, ParseError
from token_management.services.create_login_token import LoginTokenService


class AuthBearer(HttpBearer):
    def authenticate(self, request, token):
        if not token:
            raise ParseError(message_code="INVALID_LOGIN_TOKEN")
        try:
            access_token = jwt.decode(
                token, settings.SECRET_KEY, algorithms=settings.JWT_ALGORITHM
            )
        except jwt.exceptions.DecodeError:
            raise AuthenticationFailed(message_code="INVALID_LOGIN_TOKEN")
        except jwt.exceptions.ExpiredSignatureError:
            raise AuthenticationFailed(message_code="INVALID_LOGIN_TOKEN")
        """Parsing JWT"""
        user_uid = access_token.get("user_uid")
        exp_time = access_token.get("exp")
        token_iden = access_token.get("token_iden")
        if user_uid is None or exp_time is None:
            raise ParseError(message_code="INVALID_LOGIN_TOKEN")
        """Check exp of JWT"""
        if datetime.fromtimestamp(exp_time) < datetime.now():
            raise AuthenticationFailed(message_code="INVALID_LOGIN_TOKEN")
        try:
            request.user = User.objects.get(uid=user_uid)
        except User.DoesNotExist:
            raise NotFound(message_code="USER_NOT_FOUND")
        if not request.user.check_active():
            raise AuthenticationFailed(message_code="USER_UNVERIFIED")

        token_identifier = LoginToken.objects.filter(
            user=request.user, token=token_iden
        )

        if token_identifier and datetime.fromtimestamp(exp_time) > datetime.now():
            raise AuthenticationFailed(message_code="INVALID_LOGIN_TOKEN")

        return token
