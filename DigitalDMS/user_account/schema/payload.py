from typing import Optional

from ninja.schema import Schema


class UserRegisterRequest(Schema):
    first_name: str
    last_name: str
    email: str
    user_name: str
    password: str
    is_expert_user: bool


class UserPasswordRegisterRequest(Schema):
    token: str
    password: str


class UserLoginRequest(Schema):
    email: str
    password: str


class UserChangePassword(Schema):
    current_password: str
    new_password: str


class UserUpdateInfoRequest(Schema):
    first_name: str
    last_name: str


class UserPasswordResetRequest(Schema):
    token: str
    password: str


class EmailRequestResponse(Schema):
    email: str


class FacebookConnectResponse(Schema):
    token: str
