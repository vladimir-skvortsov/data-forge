import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class RegisterResponse(BaseModel):
    user_id: uuid.UUID
    email: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = 'bearer'


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'


class MeResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    created_at: datetime
