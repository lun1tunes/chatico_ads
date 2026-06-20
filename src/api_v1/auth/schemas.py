from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

LocaleCode = Literal["ru", "kz", "en"]


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    locale: LocaleCode = "ru"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UpdateLocaleRequest(BaseModel):
    locale: LocaleCode


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    locale: LocaleCode
    is_active: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
